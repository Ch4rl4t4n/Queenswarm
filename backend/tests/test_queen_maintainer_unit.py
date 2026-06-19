"""Unit tests for Queen Maintainer tech health and PR workflow."""

from __future__ import annotations

from pathlib import Path

from app.application.services.queen_maintainer.pr_workflow import (
    build_branch_name,
    validate_changed_paths,
)
from app.application.services.queen_maintainer.service import build_maintainer_goal, build_post_merge_maintainer_goal
from app.application.services.queen_maintainer.tech_health import build_tech_health_report


def test_validate_changed_paths_when_denylisted_then_blocks() -> None:
    ok, blocked = validate_changed_paths(["backend/app/core/config.py", "frontend/lib/utils.ts"])
    assert ok is False
    assert "backend/app/core/config.py" in blocked


def test_validate_changed_paths_when_safe_paths_then_allows() -> None:
    ok, blocked = validate_changed_paths(["frontend/lib/utils.ts", "backend/tests/test_foo.py"])
    assert ok is True
    assert blocked == []


def test_build_branch_name_prefixes_queen_maintainer() -> None:
    branch = build_branch_name(slug="deps-bump")
    assert branch.startswith("queen-maintainer/")
    assert branch.endswith("deps-bump")


def test_build_tech_health_report_when_repo_present_then_has_scores(tmp_path: Path) -> None:
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "backend" / "requirements.txt").write_text("fastapi==0.115.0\n", encoding="utf-8")
    (tmp_path / "frontend" / "package.json").write_text(
        '{"dependencies":{"next":"15.0.0","react":"19.0.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "docs" / "harness").mkdir(parents=True)
    (tmp_path / "docs" / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md").write_text("# x", encoding="utf-8")

    report = build_tech_health_report(repo_root=tmp_path)
    assert report["backend"]["requirements_pinned_count"] >= 1
    assert report["health_score"] > 0.5


def test_build_maintainer_goal_includes_health_score() -> None:
    goal = build_maintainer_goal(tech_health={"health_score": 0.82, "signals": [], "backend": {}, "frontend": {}})
    assert "0.82" in goal
    assert "PR-only" in goal


def test_build_post_merge_maintainer_goal_includes_merge_context() -> None:
    goal = build_post_merge_maintainer_goal(
        merge_meta={
            "kind": "pull_request_merged",
            "title": "feat: rubrics",
            "base_ref": "main",
            "merge_commit_sha": "abc123456789",
            "repo_full_name": "org/repo",
        },
    )
    assert "Post-merge trigger context" in goal
    assert "feat: rubrics" in goal
    assert "org/repo" in goal


def test_is_queen_maintainer_routine_when_four_lane_tagged_then_false() -> None:
    from unittest.mock import MagicMock

    from app.application.services.queen_maintainer.service import is_queen_maintainer_routine

    row = MagicMock()
    row.context_payload = {"routine_kind": "queen_maintainer", "four_lane_id": "tech_scv"}
    assert is_queen_maintainer_routine(row) is False
