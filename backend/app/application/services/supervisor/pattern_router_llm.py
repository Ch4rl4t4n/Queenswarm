"""Optional LLM refinement hop for agentic pattern selection (P2)."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.pattern_router import (
    ALL_PATTERN_IDS,
    PATTERN_GUARDRAILS,
    PATTERN_PLANNING,
    PATTERN_REFLECTION,
    PatternSelection,
    _dedupe,
)
from app.core.config import settings
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger

logger = get_logger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def _parse_llm_refinement(raw: str) -> dict[str, Any]:
    """Extract JSON object from model output."""

    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(text)
        if match is None:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _merge_llm_refinement(
    heuristic: PatternSelection,
    *,
    add_primary: list[str],
    add_secondary: list[str],
    llm_rationale: str,
) -> PatternSelection:
    """Merge LLM suggestions into heuristic selection without dropping safety baseline."""

    merged = PatternSelection(
        primary=list(heuristic.primary),
        secondary=list(heuristic.secondary),
        forced_reflection=heuristic.forced_reflection,
        resource_aware=heuristic.resource_aware,
        rationale=list(heuristic.rationale),
        router_version="heuristic-v1+llm-v1",
    )

    for pid in add_primary:
        if pid in ALL_PATTERN_IDS and pid not in merged.primary:
            merged.primary.append(pid)
    for pid in add_secondary:
        if pid in ALL_PATTERN_IDS and pid not in merged.primary and pid not in merged.secondary:
            merged.secondary.append(pid)

    # Safety baseline — never drop core guardrails
    for required in (PATTERN_PLANNING, PATTERN_GUARDRAILS):
        if required not in merged.primary:
            merged.primary.append(required)
    if merged.forced_reflection and PATTERN_REFLECTION not in merged.primary:
        merged.primary.append(PATTERN_REFLECTION)

    merged.primary = _dedupe(merged.primary)
    merged.secondary = _dedupe([p for p in merged.secondary if p not in merged.primary])

    if llm_rationale.strip():
        merged.rationale.append(f"llm refine: {llm_rationale.strip()[:240]}")

    return merged


async def refine_pattern_selection_with_llm(
    db: AsyncSession,
    *,
    heuristic: PatternSelection,
    goal: str,
    roles: list[str] | None,
    litellm_router: LiteLLMRouter | None = None,
    swarm_id: str = "",
    task_id: str = "",
) -> PatternSelection:
    """Optional cheap LLM hop to refine heuristic pattern stack.

    Falls back to heuristic selection on any failure — never blocks session creation.
    """

    if not settings.supervisor_pattern_router_llm_enabled:
        return heuristic

    router = litellm_router or LiteLLMRouter()
    role_text = ", ".join(roles or [])
    catalog = ", ".join(sorted(ALL_PATTERN_IDS))

    prompt = (
        "Refine agentic design pattern selection for a supervisor swarm.\n"
        f"Goal: {(goal or '').strip()[:800]}\n"
        f"Roles: {role_text}\n"
        f"Heuristic primary: {', '.join(heuristic.primary)}\n"
        f"Heuristic secondary: {', '.join(heuristic.secondary)}\n"
        f"Valid pattern IDs: {catalog}\n\n"
        'Return JSON only: {"add_primary": ["id"], "add_secondary": ["id"], "rationale": "one sentence"}\n'
        "Rules: max 2 total additions; use valid IDs only; never remove guardrails or reflection."
    )

    try:
        content, _cost = await router.complete_with_fallback_messages(
            db,
            messages=[
                {"role": "system", "content": "You output compact JSON only — no markdown."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=256,
            temperature=0.2,
            swarm_id=swarm_id,
            task_id=task_id or "pattern-router-llm",
        )
        payload = _parse_llm_refinement(content)
        add_primary = [str(p) for p in list(payload.get("add_primary") or []) if str(p) in ALL_PATTERN_IDS][:2]
        add_secondary = [str(p) for p in list(payload.get("add_secondary") or []) if str(p) in ALL_PATTERN_IDS][:2]
        llm_rationale = str(payload.get("rationale") or "")

        if not add_primary and not add_secondary and not llm_rationale:
            return heuristic

        refined = _merge_llm_refinement(
            heuristic,
            add_primary=add_primary,
            add_secondary=add_secondary,
            llm_rationale=llm_rationale,
        )
        logger.info(
            "pattern_router.llm_refined",
            agent_id="pattern_router",
            swarm_id=swarm_id or "unknown",
            task_id=task_id or "pattern-router-llm",
            added_primary=add_primary,
            added_secondary=add_secondary,
        )
        return refined
    except Exception as exc:  # noqa: BLE001 — refinement is best-effort
        logger.warning(
            "pattern_router.llm_refine_failed",
            agent_id="pattern_router",
            swarm_id=swarm_id or "unknown",
            task_id=task_id or "pattern-router-llm",
            error=str(exc)[:240],
        )
        return heuristic


__all__ = ["refine_pattern_selection_with_llm"]
