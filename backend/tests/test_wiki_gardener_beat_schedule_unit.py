"""Beat schedule includes Wiki Gardener sweep when wiki layer is enabled."""

from __future__ import annotations

from app.core import config as config_module
from app.worker.beat_schedule import build_beat_schedule


def test_beat_schedule_includes_wiki_gardener_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "wiki_layer_enabled", True)
    monkeypatch.setattr(config_module.settings, "wiki_layer_gardener_sweep_enabled", True)
    schedule = build_beat_schedule()
    assert "hive-wiki-gardener-sweep" in schedule
    entry = schedule["hive-wiki-gardener-sweep"]
    assert entry["task"] == "hive.wiki_gardener_sweep_tick"


def test_beat_schedule_omits_wiki_gardener_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "wiki_layer_enabled", False)
    monkeypatch.setattr(config_module.settings, "wiki_layer_gardener_sweep_enabled", True)
    schedule = build_beat_schedule()
    assert "hive-wiki-gardener-sweep" not in schedule
