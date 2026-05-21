"""Unit tests for Dump & Sleep overnight ingest helpers."""

from __future__ import annotations

from app.application.services.dump_sleep_service import (
    DumpSleepService,
    _build_briefing_md,
    _count_stalled_signals,
)
from app.application.services.platform_features import resolve_platform_features


def test_count_stalled_signals_when_blocked_language_then_positive() -> None:
    texts = ["Project Alpha is stalled waiting on legal.", "All good here."]
    assert _count_stalled_signals(texts=texts) >= 2


def test_build_briefing_md_includes_pollen_and_priorities() -> None:
    md = _build_briefing_md(
        items_ingested=3,
        file_count=2,
        stalled_signals=1,
        pollen_earned=7.5,
        dream_digest="Consolidated insight summary.",
        voice_note="Finish taxes tomorrow",
    )
    assert "Pollen earned" in md
    assert "7.5" in md
    assert "Morning priorities" in md
    assert "Consolidated insight" in md


def test_commercial_pro_enables_dump_sleep_feature() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier="pro",
    )
    assert features["dump_sleep"] is True


def test_commercial_free_blocks_dump_sleep_feature() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier="free",
    )
    assert features["dump_sleep"] is False


def test_dump_sleep_service_repr() -> None:
    assert DumpSleepService.__name__ == "DumpSleepService"
