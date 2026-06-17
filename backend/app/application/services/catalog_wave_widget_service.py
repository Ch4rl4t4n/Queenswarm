"""MK9 — Catalog wave widget for Mission Home (MK6 scale to 50+ listings)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.factory_catalog_wave import (
    MK6_TARGET_LISTINGS,
    FactoryCatalogWaveOut,
    build_factory_catalog_wave,
)
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)


class CatalogWaveWidgetOut(BaseModel):
    """MK6 factory catalog wave snapshot for solo Mission Home."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    current_wave: str = "wave_0"
    target_next: int = 25
    mk6_target: int = MK6_TARGET_LISTINGS
    scorecard_clean_count: int = 0
    catalog_deduped_count: int = 0
    gap_to_next_wave: int = 0
    gap_to_mk6: int = 0
    seed_pending_count: int = 0
    wave_complete: bool = False
    operator_hint: str = ""
    factory_href: str = "/apps-tools/skill-factory"
    catalog_href: str = "/skills"
    pending_seeds_preview: list[str] = Field(default_factory=list)


def compose_catalog_wave_widget_snapshot() -> CatalogWaveWidgetOut:
    """Build MK6 wave progress for Mission Home."""

    if not settings.catalog_wave_mission_home_enabled:
        return CatalogWaveWidgetOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            operator_hint="Catalog wave widget disabled.",
        )

    wave: FactoryCatalogWaveOut = build_factory_catalog_wave()
    marketing_origin = (settings.marketing_public_origin or "https://letagentscook.org").strip().rstrip("/")
    wave_complete = wave.gap_to_mk6 <= 0
    progress_pct = 0
    if wave.mk6_target > 0:
        progress_pct = min(100, int(round(100 * wave.scorecard_clean_count / wave.mk6_target)))

    if wave_complete:
        hint = (
            f"MK6 target met ({wave.scorecard_clean_count}/{wave.mk6_target}) — "
            "drive traffic to letagentscook.org and use Launch & verify for live Gumroad listings."
        )
    elif wave.gap_to_next_wave > 0 and wave.seed_pending_count > 0:
        hint = wave.next_operator_action
    else:
        hint = wave.next_operator_action or "Run Factory → export → Launch & verify on Mission Home."

    _logger.info(
        "catalog_wave_widget.composed",
        agent_id="catalog_wave_widget",
        current_wave=wave.current_wave,
        scorecard_clean=wave.scorecard_clean_count,
        gap_mk6=wave.gap_to_mk6,
        progress_pct=progress_pct,
    )

    return CatalogWaveWidgetOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        current_wave=wave.current_wave,
        target_next=wave.target_next,
        mk6_target=wave.mk6_target,
        scorecard_clean_count=wave.scorecard_clean_count,
        catalog_deduped_count=wave.catalog_deduped_count,
        gap_to_next_wave=wave.gap_to_next_wave,
        gap_to_mk6=wave.gap_to_mk6,
        seed_pending_count=wave.seed_pending_count,
        wave_complete=wave_complete,
        operator_hint=hint,
        factory_href="/apps-tools/skill-factory",
        catalog_href=f"{marketing_origin}/skills",
        pending_seeds_preview=wave.pending_seeds_preview,
    )


__all__ = ["CatalogWaveWidgetOut", "compose_catalog_wave_widget_snapshot"]
