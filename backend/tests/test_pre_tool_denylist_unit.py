"""Unit tests for Queen Maintainer pre-tool denylist."""

from __future__ import annotations

from app.application.services.queen_maintainer.pre_tool_denylist import (
    pre_tool_denylist_summary,
    scan_maintainer_text_for_violations,
)


def test_scan_maintainer_text_when_clean_then_empty() -> None:
    assert scan_maintainer_text_for_violations("Add unit tests for viability gate") == []


def test_scan_maintainer_text_when_force_push_then_blocked() -> None:
    hits = scan_maintainer_text_for_violations("Run git push --force origin main")
    assert "force_push_main" in hits or "force_push" in hits


def test_scan_maintainer_text_when_deploy_prod_then_blocked() -> None:
    hits = scan_maintainer_text_for_violations("./scripts/deploy-prod.sh --env-file .env.prod")
    assert "deploy_prod" in hits


def test_pre_tool_denylist_summary_returns_labels() -> None:
    rows = pre_tool_denylist_summary()
    assert len(rows) >= 8
    assert all("id" in row and "label" in row for row in rows)
