"""Unit tests for MK9 catalog wave Mission Home widget."""

from __future__ import annotations

import pytest

from app.application.services.catalog_wave_widget_service import compose_catalog_wave_widget_snapshot


def test_catalog_wave_widget_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "catalog_wave_mission_home_enabled", False)

    snapshot = compose_catalog_wave_widget_snapshot()

    assert snapshot.enabled is False
    assert "disabled" in snapshot.operator_hint.lower()


def test_catalog_wave_widget_delegates_to_mk6_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_catalog_wave import FactoryCatalogWaveOut
    from app.core.config import settings

    monkeypatch.setattr(settings, "catalog_wave_mission_home_enabled", True)
    monkeypatch.setattr(settings, "marketing_public_origin", "https://letagentscook.org")
    monkeypatch.setattr(
        "app.application.services.catalog_wave_widget_service.build_factory_catalog_wave",
        lambda export_root=None: FactoryCatalogWaveOut(
            current_wave="wave_1",
            target_next=25,
            scorecard_clean_count=18,
            catalog_deduped_count=14,
            gap_to_next_wave=7,
            gap_to_mk6=32,
            seed_pending_count=3,
            pending_seeds_preview=["newsletter-growth", "seo-pipeline"],
            next_operator_action="Run Skill Factory on pending seeds.",
        ),
    )

    snapshot = compose_catalog_wave_widget_snapshot()

    assert snapshot.enabled is True
    assert snapshot.current_wave == "wave_1"
    assert snapshot.scorecard_clean_count == 18
    assert snapshot.gap_to_mk6 == 32
    assert snapshot.wave_complete is False
    assert snapshot.catalog_href == "https://letagentscook.org/skills"
    assert len(snapshot.pending_seeds_preview) == 2


def test_catalog_wave_widget_complete_when_mk6_met(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_catalog_wave import FactoryCatalogWaveOut
    from app.core.config import settings

    monkeypatch.setattr(settings, "catalog_wave_mission_home_enabled", True)
    monkeypatch.setattr(
        "app.application.services.catalog_wave_widget_service.build_factory_catalog_wave",
        lambda export_root=None: FactoryCatalogWaveOut(
            current_wave="complete",
            target_next=50,
            scorecard_clean_count=52,
            gap_to_next_wave=0,
            gap_to_mk6=0,
            next_operator_action="MK6 target met.",
        ),
    )

    snapshot = compose_catalog_wave_widget_snapshot()

    assert snapshot.wave_complete is True
    assert "mk6 target met" in snapshot.operator_hint.lower()
