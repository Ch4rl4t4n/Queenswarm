"""LiteLLM routing with Grok → Claude → GPT-4o-mini fallbacks + Cost Governor ledger."""

from __future__ import annotations

import json
from typing import Any

import litellm
from litellm import AuthenticationError, acompletion
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cost_governor import BudgetExceededError, CostGovernor
from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import observe_llm_cost_usd
from app.models.cost import CostRecord
from app.services.llm_runtime_credentials import (
    provider_effective_anthropic,
    provider_effective_grok,
    provider_effective_openai,
)

def _decomposition_exhaustion_message(errors: list[str]) -> str:
    """Summarize LiteLLM hop failures plus operator-visible remediation."""

    joined = "; ".join(errors)
    blob = joined.lower()
    bullets: list[str] = []

    grok_budget = ("403" in joined or "permission" in blob) and (
        "x.ai" in blob or "/v1/chat/completions" in blob or "grok" in blob
    )
    if grok_budget or ("doesn't have any credits or licenses" in blob):
        bullets.append(
            "Grok (x.ai): platba / kredit tímu alebo licencia — doplnenie v konzole x.ai alebo zmeň WORKFLOW_BREAKER_PRIMARY_MODEL.",
        )

    if "anthropic" in blob or "claude" in blob:
        if "404" in joined or "not_found" in blob or "not found" in blob:
            bullets.append(
                "Anthropic: over platný API kľúč; starý slug modelu vie vrátiť 404 — skús FALLBACK ako "
                f"{settings.workflow_breaker_fallback_model!s} alebo nastav vlastný WORKFLOW_BREAKER_FALLBACK_MODEL.",
            )

    tertiary = settings.workflow_breaker_tertiary_model
    if not model_slug_has_configured_credentials(tertiary):
        bullets.append(
            f"Tretí hop ({tertiary}) sa v reťazi nevzal — nastav použiteľný OPENAI_API_KEY v .env alebo ulož kľúč v nastavení "
            "\"LLM keys\" dashbordu (lacný záložný model).",
        )

    headline = f"LiteLLM router exhausted decomposition models: {joined}"
    if not bullets:
        return headline
    return f"{headline}\n\n---\nČo ďalej:\n" + "\n".join(f"• {b}" for b in bullets)


logger = get_logger(__name__)


def model_api_key(model: str) -> str:
    """Return provider API key for the LiteLLM model slug."""

    lowered = model.lower()
    if lowered.startswith("xai/") or "grok" in lowered:
        return provider_effective_grok()
    if lowered.startswith("anthropic/") or lowered.startswith("claude"):
        return provider_effective_anthropic()
    if lowered.startswith("openai/") or "gpt" in lowered:
        key = provider_effective_openai()
        if not key:
            msg = "OpenAI routing requested but OPENAI_API_KEY is unset."
            raise RuntimeError(msg)
        return key
    msg = f"Unsupported LiteLLM model slug for credential resolution: {model}"
    raise ValueError(msg)


def _openai_key_looks_configured(raw: str | None) -> bool:
    """Return False for empty or obvious template `.env` placeholders."""

    if raw is None:
        return False
    token = str(raw).strip()
    if len(token) < 20:
        return False
    lower = token.lower()
    if lower.startswith("your_") or lower.startswith("sk-placeholder") or "changeme" in lower:
        return False
    return True


def model_slug_has_configured_credentials(model_name: str) -> bool:
    """Return ``True`` when ``model_name`` can be routed without empty API keys."""

    lowered = model_name.lower()
    if lowered.startswith("xai/") or "grok" in lowered:
        return bool(provider_effective_grok())
    if lowered.startswith("anthropic/") or lowered.startswith("claude") or "claude-" in lowered:
        return bool(provider_effective_anthropic())
    if lowered.startswith("openai/") or "gpt-" in lowered or "/gpt" in lowered:
        return _openai_key_looks_configured(provider_effective_openai())
    try:
        key = model_api_key(model_name)
    except (ValueError, RuntimeError):
        return False
    return bool(str(key).strip())


async def record_llm_cost(
    session: AsyncSession,
    *,
    response: Any,
    model_name: str,
    agent_id: object | None = None,
    task_id: object | None = None,
) -> None:
    """Persist a coarse CostRecord when LiteLLM returns token + cost telemetry."""

    try:
        prompt_tokens = 0
        completion_tokens = 0
        usage = getattr(response, "usage", None)
        if isinstance(response, dict) and usage is None:
            usage = response.get("usage")
        if usage is None:
            return
        if isinstance(usage, dict):
            prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            completion_tokens = int(
                usage.get("completion_tokens") or usage.get("output_tokens") or 0,
            )
        else:
            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        billed = litellm.completion_cost(completion_response=response, model=model_name)
        cost_value = float(billed or 0.0)
        if cost_value == 0.0 and prompt_tokens == 0 and completion_tokens == 0:
            return
        entry = CostRecord(
            agent_id=agent_id,
            task_id=task_id,
            llm_model=model_name,
            tokens_in=prompt_tokens,
            tokens_out=completion_tokens,
            cost_usd=max(cost_value, 0.0),
        )
        session.add(entry)
    except Exception as exc:  # noqa: BLE001 — ledger is best-effort
        logger.warning(
            "llm_router.cost.unavailable",
            model=model_name,
            error_type=type(exc).__name__,
            error=str(exc),
        )


class LiteLLMRouter:
    """Route LLM calls with cost/speed/quality tradeoffs and ledger inserts."""

    def __init__(self) -> None:
        """Create a router backed by global hive ``settings``."""

        self._governor = CostGovernor()

    def _decomposition_chain(self) -> list[str]:
        """Ordered list of model slugs that have usable credentials."""

        ordered: list[str] = [
            settings.workflow_breaker_primary_model,
            settings.workflow_breaker_fallback_model,
            settings.workflow_breaker_tertiary_model,
        ]
        seen: set[str] = set()
        usable: list[str] = []
        for name in ordered:
            if name in seen:
                continue
            seen.add(name)
            if not model_slug_has_configured_credentials(name):
                logger.info("llm_router.decompose.skip_missing_credentials", model=name)
                continue
            usable.append(name)
        return usable

    async def _assert_budget(self, session: AsyncSession) -> None:
        """Block work when the daily envelope is already exceeded."""

        await self._governor.assert_can_spend(session, delta_usd=0.0)

    async def _acompletion_with_model(
        self,
        session: AsyncSession,
        *,
        model_name: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        agent_id: object | None = None,
        task_id: object | None = None,
    ) -> tuple[Any, str, str, float]:
        """Invoke a single model and attach CostRecord rows when telemetry exists.

        Returns:
            Tuple of LiteLLM response object, textual content, model slug used, and billed USD estimate.
        """

        await self._assert_budget(session)
        api_key = model_api_key(model_name)
        lowered_m = model_name.lower()
        completion_kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.workflow_breaker_temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.workflow_breaker_max_output_tokens,
            "api_key": api_key,
        }
        if lowered_m.startswith("xai/"):
            # LiteLLM 1.49 treats ``xai/`` inconsistently — use xAI OpenAI-compat surface.
            slug = model_name.split("/", 1)[1]
            completion_kwargs["model"] = f"openai/{slug}"
            completion_kwargs["api_base"] = str(settings.xai_openai_compatible_base).rstrip("/")
        response = await acompletion(
            **completion_kwargs,
        )
        content = response.choices[0].message.content or ""
        hop_cost_usd = float(litellm.completion_cost(completion_response=response, model=model_name) or 0.0)
        observe_llm_cost_usd(model_name=model_name, cost_usd=hop_cost_usd)
        await record_llm_cost(
            session,
            response=response,
            model_name=model_name,
            agent_id=agent_id,
            task_id=task_id,
        )
        logger.info(
            "llm_router.completion.ok",
            model=model_name,
            agent_id=str(agent_id) if agent_id else "",
            task_id=str(task_id) if task_id else "",
            hop_cost_usd=hop_cost_usd,
        )
        return response, content, model_name, hop_cost_usd

    async def complete_with_fallback_messages(
        self,
        session: AsyncSession,
        *,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        swarm_id: str = "",
        workflow_id: str | None = None,
        task_id: str | None = None,
    ) -> tuple[str, float]:
        """Try Grok → Claude → optional GPT using the configured decomposition chain.

        Returns:
            Model text and billed USD estimate for the successful hop.
        """

        errors: list[str] = []
        bind = {
            "agent_id": None,
            "swarm_id": swarm_id,
            "task_id": task_id or "",
            "workflow_id": workflow_id or "",
        }
        hops = self._decomposition_chain()
        if not hops:
            raise RuntimeError(
                "LiteLLM router has no credentials for configured models "
                "(set GROK_API_KEY, ANTHROPIC_API_KEY, and/or OPENAI_API_KEY).",
            )
        for model_name in hops:
            try:
                await self._assert_budget(session)
                _response, content, used, hop_cost_usd = await self._acompletion_with_model(
                    session,
                    model_name=model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                logger.info(
                    "llm_router.completion_chain.ok",
                    model=used,
                    **bind,
                    hop_cost_usd=hop_cost_usd,
                )
                return content, hop_cost_usd
            except BudgetExceededError:
                logger.error(
                    "llm_router.completion_chain.budget_blocked",
                    model=model_name,
                    **bind,
                )
                raise
            except AuthenticationError as exc:
                errors.append(f"{model_name}: {exc}")
                logger.warning(
                    "llm_router.completion_chain.auth_failed_hop",
                    model=model_name,
                    error=str(exc),
                    **bind,
                )
                continue
            except Exception as exc:  # noqa: BLE001 — hop-specific failures
                errors.append(f"{model_name}: {exc}")
                logger.warning(
                    "llm_router.completion_chain.hop_failed",
                    model=model_name,
                    error=str(exc),
                    **bind,
                )
                continue
        raise RuntimeError(_decomposition_exhaustion_message(errors))

    async def decompose(
        self,
        session: AsyncSession,
        *,
        system_prompt: str,
        user_payload: str,
        swarm_id: str = "",
        workflow_id: str | None = None,
        task_id: str | None = None,
    ) -> tuple[str, float]:
        """Run Grok → Claude → (optional) GPT-4o-mini until one provider succeeds.

        Args:
            session: Active SQLAlchemy async session for spend rows.
            system_prompt: Breaker system contract.
            user_payload: JSON user envelope (task + hints).
            swarm_id: Hive trace id.
            workflow_id: Breaker workflow lineage.
            task_id: Optional backlog link.

        Returns:
            Raw textual model output and estimated USD cost for the successful completion hop.

        Raises:
            AuthenticationError: When credentials are rejected by a provider.
            RuntimeError: When every hop fails or budget blocks execution.
            BudgetExceededError: When Cost Governor rejects additional spend.
        """

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ]
        return await self.complete_with_fallback_messages(
            session,
            messages=messages,
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            task_id=task_id,
        )

    async def evaluate(
        self,
        session: AsyncSession,
        *,
        text: str,
        criteria: dict[str, Any],
        swarm_id: str = "",
        workflow_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Call the configured evaluator (typically Claude) for rubric scoring."""

        from app.workflows.prompts import EVALUATION_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps({"text": text, "evaluation_criteria": criteria}, default=str),
            },
        ]
        bind = {
            "agent_id": None,
            "swarm_id": swarm_id,
            "task_id": task_id or "",
            "workflow_id": workflow_id or "",
        }
        await self._assert_budget(session)
        _response, content, model_used, _hop_cost = await self._acompletion_with_model(
            session,
            model_name=settings.workflow_breaker_evaluation_model,
            messages=messages,
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "llm_router.evaluate.non_json",
                model=model_used,
                content_preview=content[:400],
                **bind,
            )
            return {
                "is_valid": False,
                "confidence": 0.0,
                "feedback": content[:2000],
                "raw_model": model_used,
            }
        if isinstance(parsed, dict):
            parsed.setdefault("raw_model", model_used)
            return parsed
        return {"is_valid": False, "confidence": 0.0, "feedback": str(parsed), "raw_model": model_used}

    async def simulate(
        self,
        session: AsyncSession,
        *,
        scenario: dict[str, Any],
        swarm_id: str = "",
        workflow_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Call the cheap simulation model (typically GPT-4o-mini)."""

        from app.workflows.prompts import SIMULATION_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": SIMULATION_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(scenario, default=str)},
        ]
        bind = {
            "agent_id": None,
            "swarm_id": swarm_id,
            "task_id": task_id or "",
            "workflow_id": workflow_id or "",
        }
        await self._assert_budget(session)
        _response, content, model_used, _hop_cost = await self._acompletion_with_model(
            session,
            model_name=settings.workflow_breaker_simulation_model,
            messages=messages,
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "llm_router.simulate.non_json",
                model=model_used,
                content_preview=content[:400],
                **bind,
            )
            return {
                "result": {"preview": content[:2000]},
                "confidence_pct": 0.0,
                "raw_model": model_used,
            }
        if isinstance(parsed, dict):
            parsed.setdefault("raw_model", model_used)
            return parsed
        return {"result": {}, "confidence_pct": 0.0, "raw": parsed, "raw_model": model_used}


async def llm_complete(
    prompt: str,
    system: str | None = None,
    *,
    max_tokens: int = 1000,
    temperature: float = 0.3,
    reload_vault_first: bool = False,
    swarm_id: str = "",
    workflow_id: str | None = None,
    task_id: str | None = None,
) -> str:
    """Run the Grok-first fallback chain outside workflow breaker callers (tests, tooling)."""

    from app.core.database import async_session
    from app.models import load_all_models
    from app.services.llm_runtime_credentials import refresh_llm_secret_cache

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    load_all_models()
    async with async_session() as session:
        if reload_vault_first:
            await refresh_llm_secret_cache(session)
        router = LiteLLMRouter()
        text, _cost = await router.complete_with_fallback_messages(
            session,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            task_id=task_id,
        )
        await session.commit()
        return (text or "").strip()


def load_keys_from_vault() -> None:
    """Decrypt vault secrets and mirror keys into ``os.environ`` (sync CLI helper)."""

    import asyncio

    from app.core.database import async_session
    from app.models import load_all_models
    from app.services.llm_runtime_credentials import refresh_llm_secret_cache

    async def _go() -> None:
        load_all_models()
        async with async_session() as session:
            await refresh_llm_secret_cache(session)
            await session.commit()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_go())
    else:
        logger.warning(
            "load_keys_from_vault_skipped_running_loop",
            message="use refresh_llm_secret_cache(session) inside async lifespan",
        )


__all__ = [
    "LiteLLMRouter",
    "llm_complete",
    "load_keys_from_vault",
    "model_api_key",
    "model_slug_has_configured_credentials",
    "record_llm_cost",
]
