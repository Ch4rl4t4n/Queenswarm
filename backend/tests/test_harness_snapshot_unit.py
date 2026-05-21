"""Unit tests for harness snapshot and forager intelligence scan."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.application.services.forager_intelligence import run_intelligence_scan
from app.application.services.harness_snapshot import build_harness_snapshot


@pytest.mark.asyncio
async def test_build_harness_snapshot_includes_skills_and_flags() -> None:
    payload = await build_harness_snapshot(None)
    assert payload["skills"]["count"] >= 1
    assert "reference_mode_count" in payload["skills"]
    assert "supervisor_pattern_router_enabled" in payload["feature_flags"]
    assert "supervisor_pattern_router_llm_enabled" in payload["feature_flags"]
    assert "skill_lazy_reference_fetch_enabled" in payload["feature_flags"]
    assert isinstance(payload["rule_layers"], list)
    assert "monitoring" in payload
    assert payload["monitoring"]["grafana_dashboard_uid"] == "queenswarm-agentic-patterns"
    assert len(payload["monitoring"]["pattern_alert_rules"]) == 3
    assert "queen_maintainer" in payload
    assert "post_merge_webhook" in payload["queen_maintainer"]


def test_run_intelligence_scan_returns_proposals() -> None:
    result = run_intelligence_scan()
    assert "proposal_count" in result
    assert "proposals" in result
    assert isinstance(result["proposals"], list)


def test_run_intelligence_scan_when_doc_missing_proposes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.forager_intelligence.resolve_repo_root",
        lambda: tmp_path,
    )
    result = run_intelligence_scan()
    kinds = {item["kind"] for item in result["proposals"]}
    assert "missing_harness_doc" in kinds
