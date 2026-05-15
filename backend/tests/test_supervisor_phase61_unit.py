"""Unit tests for Phase 6.1 supervisor skills/retrieval/routines helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.services.supervisor.routine_service import compute_next_run_at
from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.skills import SkillLibrary


def test_skill_library_resolve_slugs_when_role_defaults_then_filters_existing(tmp_path) -> None:
    """Role defaults are resolved only when backing Markdown files exist."""

    (tmp_path / "context.md").write_text("# Context\nHello", encoding="utf-8")
    (tmp_path / "decide.md").write_text("# Decide\nWorld", encoding="utf-8")
    lib = SkillLibrary(skills_dir=tmp_path)
    out = lib.resolve_slugs(role="designer", requested=["missing", "context"])
    assert out == ["context", "decide"]


def test_skill_library_build_prompt_block_when_valid_slugs_then_includes_titles(tmp_path) -> None:
    """Prompt block concatenates selected skill markdown in deterministic order."""

    (tmp_path / "tdd.md").write_text("# TDD\nred-green", encoding="utf-8")
    lib = SkillLibrary(skills_dir=tmp_path)
    block = lib.build_prompt_block(["tdd"])
    assert "Skill: TDD" in block
    assert "red-green" in block


def test_retrieval_contract_parse_when_known_sections_then_keeps_order() -> None:
    """Retrieval contract parser keeps known tokens and removes duplicates."""

    svc = SharedContextService()
    out = svc.parse_retrieval_contract("policy+last_3_tasks,policy,graph_context")
    assert out == ["policy", "last_3_tasks", "graph_context"]


def test_compute_next_run_at_interval_when_small_then_clamps_to_minute() -> None:
    """Interval scheduler enforces a minimum cadence of 60 seconds."""

    now = datetime(2026, 1, 1, tzinfo=UTC)
    nxt = compute_next_run_at(now=now, schedule_kind="interval", interval_seconds=1, cron_expr=None)
    assert int((nxt - now).total_seconds()) == 60


def test_compute_next_run_at_daily_cron_when_alias_then_next_midnight() -> None:
    """Daily cron alias rounds to next midnight in UTC."""

    now = datetime(2026, 1, 1, 22, 15, tzinfo=UTC)
    nxt = compute_next_run_at(now=now, schedule_kind="cron", interval_seconds=None, cron_expr="@daily")
    assert nxt.hour == 0 and nxt.minute == 0
