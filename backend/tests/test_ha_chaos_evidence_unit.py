"""Unit tests for HA chaos evidence loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.services.ha_chaos_evidence import load_latest_ha_chaos_evidence


def test_load_latest_ha_chaos_evidence_when_json_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Latest JSON sidecar is parsed into HA chaos evidence."""

    reports = tmp_path / "ha"
    reports.mkdir()
    older = reports / "ha-chaos-20260101T120000Z.json"
    newer = reports / "ha-chaos-20260201T120000Z.json"
    older.write_text(json.dumps({"timestamp_utc": "2026-01-01T12:00:00Z", "passed": False}), encoding="utf-8")
    newer.write_text(
        json.dumps(
            {
                "timestamp_utc": "2026-02-01T12:00:00+00:00",
                "passed": True,
                "baseline_ready_code": 200,
                "degraded_ready_code": 503,
                "recovered_ready_code": 200,
                "report_file": "ha-chaos-20260201T120000Z.json",
            },
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("app.application.services.ha_chaos_evidence.settings.ha_reports_dir", str(reports))

    evidence = load_latest_ha_chaos_evidence()
    assert evidence["report_available"] is True
    assert evidence["passed"] is True
    assert evidence["degraded_ready_code"] == 503


def test_load_latest_ha_chaos_evidence_when_dir_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing reports directory returns empty evidence."""

    monkeypatch.setattr("app.application.services.ha_chaos_evidence.settings.ha_reports_dir", "/nonexistent/ha")
    evidence = load_latest_ha_chaos_evidence()
    assert evidence["report_available"] is False
