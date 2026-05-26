"""Unit tests for operator next action resolver."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.services.operator_next_action import resolve_operator_next_action
from app.application.services.operator_social_oauth_status import OperatorSocialOAuthStatusOut
from app.application.services.publish_operator_onboarding import (
    PublishOnboardingSnapshotOut,
    PublishOnboardingStepOut,
)
from app.core.config import settings


def test_resolve_next_action_oauth_env_missing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "social_publish_live_enabled", False)
    onboarding = PublishOnboardingSnapshotOut(
        generated_at=datetime.now(tz=UTC),
        progress_pct=50,
        steps=[
            PublishOnboardingStepOut(
                id="brain_pack",
                label="Brain Pack",
                status="done",
                detail="ok",
                link=None,
            ),
            PublishOnboardingStepOut(
                id="oauth",
                label="OAuth",
                status="pending",
                detail="pending",
                link="/hub",
            ),
        ],
    )
    oauth = OperatorSocialOAuthStatusOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        env_configured_count=0,
        active_channel_count=0,
    )
    action = resolve_operator_next_action(publish_onboarding=onboarding, social_oauth=oauth)
    assert action.step_id == "oauth_env"
    assert "OAuth" in action.title


def test_resolve_next_action_live_flag(monkeypatch) -> None:
    monkeypatch.setattr(settings, "social_publish_live_enabled", False)
    onboarding = PublishOnboardingSnapshotOut(
        generated_at=datetime.now(tz=UTC),
        progress_pct=80,
        steps=[
            PublishOnboardingStepOut(
                id="simulate_publish",
                label="Simulate",
                status="done",
                detail="ok",
                link=None,
            ),
        ],
    )
    oauth = OperatorSocialOAuthStatusOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        env_configured_count=1,
        active_channel_count=1,
    )
    action = resolve_operator_next_action(publish_onboarding=onboarding, social_oauth=oauth)
    assert action.step_id == "live_flag"
    assert "live" in action.title.lower()
