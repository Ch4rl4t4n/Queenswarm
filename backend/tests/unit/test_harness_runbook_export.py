"""Unit tests for Operator Runbook export."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.application.services.harness_runbook_export import build_runbook_export_bundle, build_runbook_md


def _recipe(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "id": uuid4(),
        "name": "Weekly SEO Review",
        "description": "Supervised SEO content review loop.",
        "workflow_template": {
            "steps": [
                {"agent_role": "researcher", "description": "Gather SERP changes"},
                {"agent_role": "critic", "description": "Verdict APPROVE before publish"},
            ],
        },
        "verified_at": datetime.now(tz=UTC),
        "success_count": 8,
        "fail_count": 2,
        "avg_pollen_earned": 12.5,
        "topic_tags": ["seo"],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_build_runbook_md_includes_steps() -> None:
    md = build_runbook_md(_recipe())  # type: ignore[arg-type]
    assert "researcher" in md
    assert "RUNBOOK" in md or "Runbook" in md


def test_build_runbook_export_bundle_includes_runbook_file() -> None:
    bundle = build_runbook_export_bundle(_recipe())  # type: ignore[arg-type]
    paths = {f.path for f in bundle.files}
    assert any(p.endswith("/RUNBOOK.md") for p in paths)
    assert any(p.endswith("/SCHEDULE.template.json") for p in paths)
