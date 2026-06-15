"""MEM4 — Token budget meter for Brain Pack + HiveMind harness injection."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.brain_pack_starters import starter_kinds
from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.selective_recall import (
    effective_prompt_char_budget,
    load_recall_config,
    normalize_recall_mode,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.memory.curated import CuratedFileKind

_logger = get_logger(__name__)

BudgetStatus = Literal["ok", "warn", "critical"]

_LAYER_KINDS: dict[str, tuple[CuratedFileKind, ...]] = {
    "soul": (CuratedFileKind.SOUL, CuratedFileKind.SKILLS_HIERARCHY),
    "memory": (CuratedFileKind.MISSION, CuratedFileKind.IDEAL_STATE),
    "user": (CuratedFileKind.INSTRUCTIONS,),
    "brand": (CuratedFileKind.BRAND,),
}


class TokenBudgetLayerOut(BaseModel):
    """One Brain Pack layer char contribution."""

    model_config = ConfigDict(extra="ignore")

    layer_id: str
    label: str
    char_count: int
    estimated_tokens: int
    filled: bool


class TokenBudgetMeterOut(BaseModel):
    """Brain Pack + HiveMind recall budget snapshot for MEM4."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    prompt_prefix_chars: int = 0
    estimated_tokens: int = 0
    storage_total_chars: int = 0
    storage_max_chars: int = 0
    storage_usage_pct: int = Field(ge=0, le=100, default=0)
    recall_mode: str = "selective"
    recall_char_budget: int = 0
    estimated_recall_tokens: int = 0
    max_prompt_chars: int = 0
    selective_max_chars: int = 0
    recall_usage_pct: int = Field(ge=0, le=100, default=0)
    combined_estimated_tokens: int = 0
    status: BudgetStatus = "ok"
    operator_hint: str = "Brain Pack injection + HiveMind recall budget vs hive_mind_max_prompt_chars."
    layers: list[TokenBudgetLayerOut] = Field(default_factory=list)


def estimate_tokens(char_count: int) -> int:
    """Approximate token count from character length (≈4 chars/token)."""

    return max(0, int(char_count) // 4)


def _layer_char_count(bundle: dict[CuratedFileKind, str], kinds: tuple[CuratedFileKind, ...]) -> int:
    return sum(len((bundle.get(kind) or "").strip()) for kind in kinds)


def _resolve_status(
    *,
    prompt_prefix_chars: int,
    max_prompt_chars: int,
    recall_usage_pct: int,
) -> BudgetStatus:
    if prompt_prefix_chars > max_prompt_chars * 2:
        return "critical"
    if prompt_prefix_chars > max_prompt_chars or recall_usage_pct >= 95:
        return "critical"
    if prompt_prefix_chars > int(max_prompt_chars * 0.75) or recall_usage_pct >= 80:
        return "warn"
    return "ok"


def _operator_hint(
    *,
    status: BudgetStatus,
    prompt_prefix_chars: int,
    max_prompt_chars: int,
    recall_mode: str,
) -> str:
    if status == "critical":
        return (
            f"Brain Pack injects ~{estimate_tokens(prompt_prefix_chars)} tokens — above the "
            f"{max_prompt_chars}-char HiveMind cap reference. Trim SOUL/MEMORY/USER or tighten recall."
        )
    if status == "warn":
        return (
            "Approaching prompt budget — shorten Brain Pack layers or lower selective recall char override."
        )
    if recall_mode == "full":
        return "Full recall mode uses the hive_mind_max_prompt_chars cap for vector + graph context."
    return "Selective recall keeps HiveMind injection under budget; Brain Pack injects on every Queen bootstrap."


def derive_token_budget_meter(
    *,
    bundle: dict[CuratedFileKind, str],
    recall_mode: str,
    tenant_token_budget: int,
) -> TokenBudgetMeterOut:
    """Build MEM4 meter from curated bundle and recall settings."""

    layers: list[TokenBudgetLayerOut] = []
    storage_total = 0
    for layer_id, label, kinds in (
        ("soul", "SOUL", _LAYER_KINDS["soul"]),
        ("memory", "MEMORY", _LAYER_KINDS["memory"]),
        ("user", "USER", _LAYER_KINDS["user"]),
        ("brand", "BRAND", _LAYER_KINDS["brand"]),
    ):
        char_count = _layer_char_count(bundle, kinds)
        storage_total += char_count
        layers.append(
            TokenBudgetLayerOut(
                layer_id=layer_id,
                label=label,
                char_count=char_count,
                estimated_tokens=estimate_tokens(char_count),
                filled=char_count > 0,
            ),
        )

    mission = (bundle.get(CuratedFileKind.MISSION) or "").strip()
    ideal_state = (bundle.get(CuratedFileKind.IDEAL_STATE) or "").strip()
    soul = (bundle.get(CuratedFileKind.SOUL) or "").strip()
    skills_hierarchy = (bundle.get(CuratedFileKind.SKILLS_HIERARCHY) or "").strip()
    instructions = (bundle.get(CuratedFileKind.INSTRUCTIONS) or "").strip()
    prompt_prefix = (
        "=== MISSION ===\n"
        f"{mission}\n"
        "=== IDEAL STATE ===\n"
        f"{ideal_state}\n"
        "=== SOUL ===\n"
        f"{soul}\n"
        "=== SKILLS HIERARCHY ===\n"
        f"{skills_hierarchy}\n"
        "=== BEHAVIORAL INSTRUCTIONS ===\n"
        f"{instructions}\n"
        "=== END CONTEXT ==="
    )
    prompt_prefix_chars = len(prompt_prefix)

    max_per_file = CuratedMemoryService.max_chars_per_file()
    storage_max = max_per_file * len(starter_kinds())
    storage_usage_pct = min(100, round((storage_total / storage_max) * 100)) if storage_max else 0

    normalized_mode = normalize_recall_mode(recall_mode)
    max_prompt_chars = int(settings.hive_mind_max_prompt_chars)
    selective_max = int(settings.hive_mind_selective_recall_max_chars)
    recall_char_budget = effective_prompt_char_budget(
        recall_mode=normalized_mode,
        tenant_budget=int(tenant_token_budget or 0),
        settings_max_prompt=max_prompt_chars,
        selective_max_chars=selective_max,
    )
    recall_usage_pct = (
        min(100, round((recall_char_budget / max_prompt_chars) * 100)) if max_prompt_chars else 0
    )
    estimated_tokens = estimate_tokens(prompt_prefix_chars)
    estimated_recall_tokens = estimate_tokens(recall_char_budget)
    status = _resolve_status(
        prompt_prefix_chars=prompt_prefix_chars,
        max_prompt_chars=max_prompt_chars,
        recall_usage_pct=recall_usage_pct,
    )

    return TokenBudgetMeterOut(
        enabled=True,
        prompt_prefix_chars=prompt_prefix_chars,
        estimated_tokens=estimated_tokens,
        storage_total_chars=storage_total,
        storage_max_chars=storage_max,
        storage_usage_pct=storage_usage_pct,
        recall_mode=normalized_mode,
        recall_char_budget=recall_char_budget,
        estimated_recall_tokens=estimated_recall_tokens,
        max_prompt_chars=max_prompt_chars,
        selective_max_chars=selective_max,
        recall_usage_pct=recall_usage_pct,
        combined_estimated_tokens=estimated_tokens + estimated_recall_tokens,
        status=status,
        operator_hint=_operator_hint(
            status=status,
            prompt_prefix_chars=prompt_prefix_chars,
            max_prompt_chars=max_prompt_chars,
            recall_mode=normalized_mode,
        ),
        layers=layers,
    )


async def compose_token_budget_meter(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> TokenBudgetMeterOut:
    """Load tenant bundle + recall config and compose MEM4 token budget meter."""

    if not settings.token_budget_meter_enabled:
        return TokenBudgetMeterOut(enabled=False)

    svc = CuratedMemoryService(db=session)
    bundle = await svc.get_bundle(tenant_id)
    recall_cfg = await load_recall_config(session, tenant_id=tenant_id)
    meter = derive_token_budget_meter(
        bundle=bundle,
        recall_mode=str(recall_cfg.get("recall_mode") or "selective"),
        tenant_token_budget=int(recall_cfg.get("token_budget_chars") or 0),
    )
    _logger.info(
        "token_budget_meter.composed",
        agent_id="token_budget_meter",
        swarm_id=str(tenant_id),
        status=meter.status,
        prompt_prefix_chars=meter.prompt_prefix_chars,
        recall_char_budget=meter.recall_char_budget,
    )
    return meter


__all__ = [
    "TokenBudgetLayerOut",
    "TokenBudgetMeterOut",
    "compose_token_budget_meter",
    "derive_token_budget_meter",
    "estimate_tokens",
]
