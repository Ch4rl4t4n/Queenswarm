"""Revenue-oriented Factory presets — Pigford solo-founder + Middleton local-biz bundles."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FactoryProductPresetOut(BaseModel):
    """One operator preset mapping analysis → niche seeds + Gumroad angle."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    summary: str
    source: str
    gumroad_price_eur_cents_recommended: int
    niche_seeds: list[str] = Field(default_factory=list)
    stars: int = 3


PIGFORD_SOLO_FOUNDER_SEEDS: tuple[str, ...] = (
    "solo founder build-review-learnings harness (Cursor)",
    "adversarial multi-model code review skill pack",
    "Claude Code PR review skill for indie dev teams",
    "progress-file feature shipping workflow skill",
    "simulate-first deploy checklist skill for indie SaaS",
)

MIDDLETON_LOCAL_BIZ_5_WORKERS_SEEDS: tuple[str, ...] = (
    "local gym database reactivation email skill pack",
    "dental clinic Google reviews response automation",
    "local service business lead nurturing SMS skill",
    "small business AI receptionist FAQ skill pack",
    "local business Meta ads copy refresh runbook",
)


def factory_product_presets() -> list[FactoryProductPresetOut]:
    """Return sellable preset bundles for Skill Factory Settings UI."""

    return [
        FactoryProductPresetOut(
            id="pigford_solo_founder",
            title="Solo founder build loop",
            summary=(
                "Pigford-style pack: research → plan → implement → adversarial review → learnings "
                "distill into curated memory."
            ),
            source="Josh Pigford / Cursor skill packs",
            gumroad_price_eur_cents_recommended=4900,
            niche_seeds=list(PIGFORD_SOLO_FOUNDER_SEEDS),
            stars=3,
        ),
        FactoryProductPresetOut(
            id="middleton_local_biz_5_workers",
            title="Local biz — 5 AI workers bundle",
            summary=(
                "Middleton-style SMB bundle: reactivation, reviews, lead nurture, receptionist FAQ, "
                "ads refresh — each as verified runbook/skill."
            ),
            source="JP Middleton / lazy AI agency",
            gumroad_price_eur_cents_recommended=9900,
            niche_seeds=list(MIDDLETON_LOCAL_BIZ_5_WORKERS_SEEDS),
            stars=3,
        ),
    ]


def preset_by_id(preset_id: str) -> FactoryProductPresetOut | None:
    """Resolve preset by stable id."""

    normalized = preset_id.strip().lower()
    for row in factory_product_presets():
        if row.id == normalized:
            return row
    return None


def merged_vertical_seeds_payload() -> dict[str, list[str]]:
    """Vertical catalog including analysis-driven hero seeds."""

    from app.application.services.factory_vertical_seeds import vertical_seeds_payload

    base = vertical_seeds_payload()
    extra = list(PIGFORD_SOLO_FOUNDER_SEEDS) + list(MIDDLETON_LOCAL_BIZ_5_WORKERS_SEEDS)
    merged_skill = list(dict.fromkeys([*extra, *base["skill_factory"]]))
    return {
        **base,
        "skill_factory": merged_skill,
        "product_presets": [row.model_dump(mode="json") for row in factory_product_presets()],
    }


__all__ = [
    "MIDDLETON_LOCAL_BIZ_5_WORKERS_SEEDS",
    "PIGFORD_SOLO_FOUNDER_SEEDS",
    "FactoryProductPresetOut",
    "factory_product_presets",
    "merged_vertical_seeds_payload",
    "preset_by_id",
]
