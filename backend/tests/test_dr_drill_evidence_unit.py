"""Unit tests for DR drill evidence loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.services.dr_drill_evidence import load_latest_dr_drill_evidence


def test_load_latest_dr_drill_evidence_when_json_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Latest JSON sidecar is parsed into HA drill evidence."""

    reports = tmp_path / "dr"
    reports.mkdir()
    older = reports / "dr-drill-20260101T120000Z.json"
    newer = reports / "dr-drill-20260201T120000Z.json"
    older.write_text(json.dumps({"timestamp_utc": "2026-01-01T12:00:00Z", "backup_duration_sec": 10}), encoding="utf-8")
    newer.write_text(
        json.dumps(
            {
                "timestamp_utc": "2026-02-01T12:00:00+00:00",
                "backup_duration_sec": 42,
                "restore_status": "not-run",
                "report_file": "dr-drill-20260201T120000Z.md",
            },
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("app.application.services.dr_drill_evidence.settings.dr_reports_dir", str(reports))

    evidence = load_latest_dr_drill_evidence()
    assert evidence["report_available"] is True
    assert evidence["backup_duration_sec"] == 42
    assert evidence["restore_status"] == "not-run"


def test_load_latest_dr_drill_evidence_when_dir_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing reports directory returns empty evidence."""

    monkeypatch.setattr("app.application.services.dr_drill_evidence.settings.dr_reports_dir", "/nonexistent/dr")
    evidence = load_latest_dr_drill_evidence()
    assert evidence["report_available"] is False
