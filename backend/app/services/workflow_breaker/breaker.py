"""LLM-assisted Auto Workflow Breaker that persists LangGraph-ready workflow graphs."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import litellm
from litellm import AuthenticationError, acompletion
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.chroma_client import find_similar_recipes
from app.core.config import settings
from app.core.logging import get_logger
from app.models.cost import CostRecord
from app.models.enums import StepStatus, WorkflowStatus
from app.models.recipe import Recipe as RecipeRow
from app.models.workflow import Workflow, WorkflowStep
from app.schemas.workflow_breaker import (
    BreakerDecomposition,
    DecomposeWorkflowResponse,
    WorkflowStepBrief,
)

logger = get_logger(__name__)

_BREAKER_SYSTEM_PROMPT = """You are the Queenswarm Auto Workflow Breaker (Alice-style explicit planning).
Decompose the operator task into 3-7 atomic steps that decentralised sub-swarms can execute.
Return **only** minified JSON (no markdown fences) with this shape:
{
  "rationale": string (why this decomposition is safe for the hive),
  "parallelizable_groups": array of arrays of integers (step order indexes that may run in parallel),
  "estimated_duration_sec": integer|null (rough upper bound for the whole graph),
  "steps": [
    {
      "order": integer (1-based),
      "description": string (clear imperative instruction, >=2 words),
      "agent_role": string (one of: scraper, evaluator, simulator, reporter, trader, marketer, blog_writer, social_poster, learner, recipe_keeper),
      "input_schema": object (JSON schema hints),
      "output_schema": object (JSON schema hints),
      "guardrails": {
        "risks": [string, ...],
        "mitigations": [string, ...],
        "stop_conditions": [string, ...]
      },
      "evaluation_criteria": {
        "must_satisfy": [string, ...],
        "measurable_signals": {string: string, ...}
      }
    }
  ]
}

Rules:
1. If the task can affect money, public posts, or human-facing truth claims, include at least one `simulator` step before any `reporter`/`trader`/`social_poster`/`blog_writer` step.
2. Never fabricate credentials or bypass guardrails—encode stop conditions explicitly.
3. Parallel groups must reference existing `order` integers only.
4. JSON only.
"""


def _extract_json_object(raw: str) -> dict[str, Any]:
    """Parse the first JSON object embedded in model output."""

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, count=1, flags=re.IGNORECASE).strip()
        if text.endswith("```"):
            text = text[: text.rfind("```")].strip()
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    msg = "Workflow breaker model did not return a JSON object."
    raise ValueError(msg)


def _model_api_key(model: str) -> str:
    """Resolve provider credentials for a LiteLLM route slug."""

    lowered = model.lower()
    if lowered.startswith("xai/") or "grok" in lowered:
        return settings.grok_api_key
    if lowered.startswith("anthropic/") or lowered.startswith("claude"):
        return settings.anthropic_api_key
    if lowered.startswith("openai/") or "gpt" in lowered:
        if settings.openai_api_key is None:
            msg = "OpenAI routing requested but OPENAI_API_KEY is unset."
            raise RuntimeError(msg)
        return settings.openai_api_key
    msg = f"Unsupported workflow breaker model slug: {model}"
    raise ValueError(msg)


async def _invoke_breaker_llm(
    messages: list[dict[str, str]],
) -> tuple[Any, str, str]:
    """Call LiteLLM with primary → fallback ordering."""

    errors: list[str] = []
    for model_name in (
        settings.workflow_breaker_primary_model,
        settings.workflow_breaker_fallback_model,
    ):
        api_key = _model_api_key(model_name)
        try:
            response = await acompletion(
                model=model_name,
                messages=messages,
                temperature=settings.workflow_breaker_temperature,
                max_tokens=settings.workflow_breaker_max_output_tokens,
                api_key=api_key,
            )
            content = response.choices[0].message.content or ""
            logger.info("workflow_breaker.llm.completed", model=model_name)
            return response, content, model_name
        except AuthenticationError:
            logger.error("workflow_breaker.llm.auth_failed", model=model_name)
            raise
        except Exception as exc:  # noqa: BLE001 — provider-specific stack
            errors.append(f"{model_name}: {exc}")
            logger.warning(
                "workflow_breaker.llm.provider_error",
                model=model_name,
                error=str(exc),
            )
            continue
    joined = "; ".join(errors)
    raise RuntimeError(f"Workflow breaker exhausted all models: {joined}")


async def _record_llm_spend(
    db: AsyncSession,
    *,
    response: Any,
    model_name: str,
) -> None:
    """Attach a coarse CostGovernor ledger row when LiteLLM supplies usage telemetry."""

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
                usage.get("completion_tokens") or usage.get("output_tokens") or 0
            )
        else:
            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        billed = litellm.completion_cost(completion_response=response, model=model_name)
        cost_value = float(billed or 0.0)
        if cost_value == 0.0 and prompt_tokens == 0 and completion_tokens == 0:
            return
        entry = CostRecord(
            llm_model=model_name,
            tokens_in=prompt_tokens,
            tokens_out=completion_tokens,
            cost_usd=max(cost_value, 0.0),
        )
        db.add(entry)
    except Exception as exc:
        logger.warning(
            "workflow_breaker.cost.unavailable",
            model=model_name,
            error=str(exc),
        )


class WorkflowBreakerService:
    """Compose breaker prompts, hydrate ORM workflows, and log hive context."""

    async def build_workflow_plan(
        self,
        db: AsyncSession,
        *,
        task_text: str,
        matching_recipe_id: uuid.UUID | None = None,
        enrich_from_chroma_recipes: bool = False,
        swarm_id: str | None = None,
        agent_task_id: str | None = None,
    ) -> DecomposeWorkflowResponse:
        """Decompose ``task_text`` into persisted ``Workflow`` + ``WorkflowStep`` rows."""

        bind_contextvars(
            swarm_id=swarm_id,
            agent_id=None,
            task_id=agent_task_id,
            workflow_id=None,
        )
        logger.info(
            "workflow_breaker.start",
            task_chars=len(task_text),
            enrich_recipe_chroma=enrich_from_chroma_recipes,
        )
        try:
            if matching_recipe_id is not None:
                exists = await db.scalar(
                    select(RecipeRow.id).where(RecipeRow.id == matching_recipe_id),
                )
                if exists is None:
                    msg = "matching_recipe_id does not reference a persisted recipe."
                    raise ValueError(msg)

            recipe_hints: list[str] = []
            if enrich_from_chroma_recipes:
                try:
                    chroma_hit = await find_similar_recipes(task_text)
                except (ConnectionError, OSError, TimeoutError, ValueError, RuntimeError) as exc:
                    logger.warning("workflow_breaker.chroma_unavailable", error=str(exc))
                    chroma_hit = None
                if chroma_hit is not None:
                    recipe_hints.append(chroma_hit.model_dump_json())

            if matching_recipe_id is not None:
                recipe_row = await db.get(RecipeRow, matching_recipe_id)
                if recipe_row is not None:
                    recipe_hints.append(
                        json.dumps(
                            {
                                "recipe_name": recipe_row.name,
                                "topic_tags": recipe_row.topic_tags,
                                "template": recipe_row.workflow_template,
                            },
                            default=str,
                        ),
                    )

            user_payload = {
                "task": task_text,
                "recipe_hints": recipe_hints,
                "hive_directives": {
                    "rapid_loop_timeout_sec": settings.rapid_loop_timeout_sec,
                    "reward_threshold_pass": settings.reward_threshold_pass,
                },
            }
            messages = [
                {"role": "system", "content": _BREAKER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, default=str)},
            ]
            response, raw_content, model_used = await _invoke_breaker_llm(messages)
            await _record_llm_spend(db, response=response, model_name=model_used)

            payload = _extract_json_object(raw_content)
            draft = BreakerDecomposition.model_validate(payload)

            workflow = Workflow(
                original_task_text=task_text,
                decomposition_rationale=draft.rationale,
                status=WorkflowStatus.EXECUTING,
                total_steps=len(draft.steps),
                completed_steps=0,
                parallelizable_groups=draft.parallelizable_groups,
                matching_recipe_id=matching_recipe_id,
                estimated_duration_sec=draft.estimated_duration_sec,
            )
            db.add(workflow)
            await db.flush()

            bind_contextvars(workflow_id=str(workflow.id))

            ordered = sorted(draft.steps, key=lambda step: step.order)
            for step in ordered:
                row = WorkflowStep(
                    workflow_id=workflow.id,
                    step_order=step.order,
                    description=step.description,
                    agent_role=step.agent_role,
                    status=StepStatus.PENDING,
                    input_schema=step.input_schema,
                    output_schema=step.output_schema,
                    guardrails=step.guardrails,
                    evaluation_criteria=step.evaluation_criteria,
                )
                db.add(row)

            await db.flush()
            hydrated = await db.scalar(
                select(Workflow)
                .options(selectinload(Workflow.steps))
                .where(Workflow.id == workflow.id),
            )
            if hydrated is None:
                msg = "Failed to reload workflow after decomposition."
                raise RuntimeError(msg)

            briefs = [
                WorkflowStepBrief(
                    id=step.id,
                    step_order=step.step_order,
                    description=step.description,
                    agent_role=step.agent_role,
                )
                for step in sorted(hydrated.steps, key=lambda s: s.step_order)
            ]
            return DecomposeWorkflowResponse(
                workflow_id=hydrated.id,
                status=hydrated.status.value,
                total_steps=hydrated.total_steps,
                parallel_groups=list(hydrated.parallelizable_groups or []),
                steps=briefs,
                decomposition_rationale=hydrated.decomposition_rationale,
            )
        except ValidationError as exc:
            logger.warning("workflow_breaker.validation_failed", errors=exc.errors())
            raise
        finally:
            clear_contextvars()
