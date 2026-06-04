"""Unit tests for operator token readiness reporting."""

from __future__ import annotations

from pathlib import Path

from scripts.operator_token_readiness import TokenStatus, collect_token_statuses, render_token_readiness


def test_collect_token_statuses_reads_env_file_without_leaking_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.prod.tokens"
    env_file.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY=sk-or-real-secret",
                "SKILL_FACTORY_GUMROAD_ACCESS_TOKEN=",
                "SKILL_FACTORY_GUMROAD_LISTING_ENABLED=true",
                "GITHUB_PAT=ghp_real_secret",
                "SMTP_USER=operator@example.com",
                "SMTP_PASS=change-me",
                "NOTIFY_EMAIL=operator@example.com",
            ],
        ),
        encoding="utf-8",
    )

    statuses = collect_token_statuses(env_file)
    by_key = {status.key: status for status in statuses}

    assert by_key["OPENROUTER_API_KEY"].configured is True
    assert by_key["SKILL_FACTORY_GUMROAD_ACCESS_TOKEN"].configured is False
    assert by_key["GITHUB_PAT"].configured is True
    assert by_key["SMTP_PASS"].configured is False
    assert "real-secret" not in render_token_readiness(statuses)
    assert "ghp_real_secret" not in render_token_readiness(statuses)


def test_render_token_readiness_groups_next_actions() -> None:
    report = render_token_readiness(
        [
            TokenStatus(key="OPENROUTER_API_KEY", label="OpenRouter", configured=False, purpose="Nemotron eval"),
            TokenStatus(key="GITHUB_PAT", label="GitHub", configured=True, purpose="Teaser repos"),
        ],
    )

    assert "# Operator Token Readiness" in report
    assert "OpenRouter" in report
    assert "missing" in report
    assert "configured" in report
    assert "Add missing tokens" in report
