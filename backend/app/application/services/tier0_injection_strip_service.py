"""MEM3 — Tier-0 injection strip: Brain Pack snapshot before deep Chroma recall."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.selective_recall import (
    effective_prompt_char_budget,
    load_recall_config,
    normalize_recall_mode,
)
from app.application.services.token_budget_meter_service import estimate_tokens
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.memory.curated import CuratedFileKind

_logger = get_logger(__name__)

_TIER0_SECTIONS: tuple[tuple[str, str, CuratedFileKind], ...] = (
    ("mission", "Mission", CuratedFileKind.MISSION),
    ("ideal_state", "Ideal state", CuratedFileKind.IDEAL_STATE),
    ("soul", "Soul", CuratedFileKind.SOUL),
    ("skills_hierarchy", "Skills hierarchy", CuratedFileKind.SKILLS_HIERARCHY),
    ("instructions", "Behavioral instructions", CuratedFileKind.INSTRUCTIONS),
)


class Tier0SectionOut(BaseModel):
    """One Hermes Brain Pack section in tier-0 frozen snapshot."""

    model_config = ConfigDict(extra="ignore")

    section_id: str
    label: str
    char_count: int
    estimated_tokens: int
    preview: str
    filled: bool


class InjectionTierOut(BaseModel):
    """One injection tier in Queen prompt assembly order."""

    model_config = ConfigDict(extra="ignore")

    tier_id: str
    label: str
    order: int
    char_count: int
    estimated_tokens: int
    active: bool
    inject_timing: str
    preview: str
    sections: list[Tier0SectionOut] = Field(default_factory=list)


class Tier0InjectionStripOut(BaseModel):
    """Operator-facing tier ladder before deep Chroma search (MEM3)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    visible: bool = False
    frozen_snapshot_label: str = "Hermes Brain Pack snapshot"
    tiers: list[InjectionTierOut] = Field(default_factory=list)
    recall_mode: str = "selective"
    deep_recall_budget_chars: int = 0
    chroma_enabled: bool = False
    operator_hint: str = "Tier-0 Brain Pack injects before HiveMind vector search."
    edit_href: str = "/knowledge?tab=memory#brain-pack"


def _preview(text: str, *, limit: int = 140) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return "Empty — load Brain Pack starter."
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def _tier0_sections(bundle: dict[CuratedFileKind, str]) -> list[Tier0SectionOut]:
    rows: list[Tier0SectionOut] = []
    for section_id, label, kind in _TIER0_SECTIONS:
        content = (bundle.get(kind) or "").strip()
        rows.append(
            Tier0SectionOut(
                section_id=section_id,
                label=label,
                char_count=len(content),
                estimated_tokens=estimate_tokens(len(content)),
                preview=_preview(content),
                filled=bool(content),
            ),
        )
    return rows


def derive_tier0_injection_strip(
    *,
    bundle: dict[CuratedFileKind, str],
    wiki_prompt_block: str,
    recall_mode: str,
    tenant_token_budget: int,
    wiki_enabled: bool | None = None,
    chroma_enabled: bool | None = None,
) -> Tier0InjectionStripOut:
    """Build MEM3 tier ladder from curated bundle and recall settings."""

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
    tier0_chars = len(prompt_prefix)
    tier0_sections = _tier0_sections(bundle)
    tier0_active = any(section.filled for section in tier0_sections)

    wiki_block = (wiki_prompt_block or "").strip()
    wiki_active = bool(wiki_enabled if wiki_enabled is not None else settings.wiki_layer_enabled) and bool(wiki_block)
    wiki_chars = len(wiki_block) if wiki_active else 0

    normalized_mode = normalize_recall_mode(recall_mode)
    deep_budget = effective_prompt_char_budget(
        recall_mode=normalized_mode,
        tenant_budget=int(tenant_token_budget or 0),
        settings_max_prompt=int(settings.hive_mind_max_prompt_chars),
        selective_max_chars=int(settings.hive_mind_selective_recall_max_chars),
    )
    chroma_on = bool(chroma_enabled if chroma_enabled is not None else settings.hive_mind_chroma_enabled)

    tiers: list[InjectionTierOut] = [
        InjectionTierOut(
            tier_id="tier0",
            label="Tier-0 · Brain Pack",
            order=0,
            char_count=tier0_chars,
            estimated_tokens=estimate_tokens(tier0_chars),
            active=tier0_active,
            inject_timing="Always — frozen Hermes snapshot before RAG",
            preview=_preview(prompt_prefix.replace("===", "").replace("\n", " "), limit=180),
            sections=tier0_sections,
        ),
        InjectionTierOut(
            tier_id="tier1",
            label="Tier-1 · Wiki hot tier",
            order=1,
            char_count=wiki_chars,
            estimated_tokens=estimate_tokens(wiki_chars),
            active=wiki_active,
            inject_timing="Hot tier wiki pages before deep raw search",
            preview=_preview(wiki_block.replace("===", "").replace("\n", " "), limit=160),
        ),
        InjectionTierOut(
            tier_id="tier2",
            label="Tier-2 · Chroma deep recall",
            order=2,
            char_count=deep_budget,
            estimated_tokens=estimate_tokens(deep_budget),
            active=chroma_on and settings.hive_mind_enabled,
            inject_timing="On query — vector + graph neighbours after tier-0/1",
            preview=(
                f"Budget {deep_budget} chars · mode {normalized_mode} · "
                "runs after frozen Brain Pack snapshot."
            ),
        ),
    ]

    visible = any(tier.active for tier in tiers[:2]) or tiers[2].active
    hint = (
        "Tier-0 Brain Pack is injected on every Queen bootstrap before HiveMind vector search."
        if tier0_active
        else "Seed Brain Pack in Knowledge — tier-0 injection is empty until SOUL/MEMORY/USER are filled."
    )

    return Tier0InjectionStripOut(
        enabled=True,
        visible=visible,
        tiers=tiers,
        recall_mode=normalized_mode,
        deep_recall_budget_chars=deep_budget,
        chroma_enabled=chroma_on,
        operator_hint=hint,
    )


async def compose_tier0_injection_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> Tier0InjectionStripOut:
    """Load tenant bundle, wiki block, and recall config for MEM3 strip."""

    if not settings.tier0_injection_strip_enabled:
        return Tier0InjectionStripOut(enabled=False, visible=False)

    curated = CuratedMemoryService(db=session)
    bundle = await curated.get_bundle(tenant_id)
    recall_cfg = await load_recall_config(session, tenant_id=tenant_id)

    wiki_block = ""
    if settings.wiki_layer_enabled:
        from app.application.services.wiki_layer_service import WikiLayerService

        wiki_block = await WikiLayerService(db=session).render_wiki_prompt_block(tenant_id)

    strip = derive_tier0_injection_strip(
        bundle=bundle,
        wiki_prompt_block=wiki_block,
        recall_mode=str(recall_cfg.get("recall_mode") or "selective"),
        tenant_token_budget=int(recall_cfg.get("token_budget_chars") or 0),
    )
    _logger.info(
        "tier0_injection_strip.composed",
        agent_id="tier0_injection_strip",
        swarm_id=str(tenant_id),
        visible=strip.visible,
        tier0_chars=strip.tiers[0].char_count if strip.tiers else 0,
        deep_recall_budget_chars=strip.deep_recall_budget_chars,
    )
    return strip


__all__ = [
    "InjectionTierOut",
    "Tier0InjectionStripOut",
    "Tier0SectionOut",
    "compose_tier0_injection_strip",
    "derive_tier0_injection_strip",
]
