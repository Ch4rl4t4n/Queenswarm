"""Operator next action — priority step derived from publish lane snapshots."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.operator_social_oauth_status import OperatorSocialOAuthStatusOut
from app.application.services.publish_operator_onboarding import PublishOnboardingSnapshotOut
from app.core.config import settings


class OperatorNextActionOut(BaseModel):
    """Single highest-priority operator action for Settings UI."""

    model_config = ConfigDict(extra="ignore")

    priority: int = 1
    title: str
    why: str
    doc: str
    commands: list[str] = Field(default_factory=list)
    ui_link: str | None = None
    step_id: str | None = None


def resolve_operator_next_action(
    *,
    publish_onboarding: PublishOnboardingSnapshotOut | None,
    social_oauth: OperatorSocialOAuthStatusOut | None,
) -> OperatorNextActionOut:
    """Pick the next publish-lane action from onboarding + OAuth snapshots."""

    if publish_onboarding is None:
        return OperatorNextActionOut(
            title="Publish lane disabled",
            why="SOCIAL_PUBLISH_ENABLED=false — enable social publish in platform env.",
            doc="docs/OPERATOR_PUBLISH_LANE_MANUAL.md",
            commands=["./scripts/operator-release-gate.sh"],
        )

    pending = [s for s in publish_onboarding.steps if s.status != "done"]
    first = pending[0] if pending else None

    if first and first.id == "brain_pack":
        return OperatorNextActionOut(
            title="Load Brain Pack starter",
            why=first.detail,
            doc="docs/SOLO_OPERATOR_TRIO_GUIDE.md",
            commands=[
                "./scripts/operator-publish-lane-prep.sh",
                "Knowledge → Curated memory → Load starter pack",
            ],
            ui_link=first.link,
            step_id=first.id,
        )

    if social_oauth and social_oauth.env_configured_count == 0:
        return OperatorNextActionOut(
            title="Add OAuth vendor keys",
            why="No OAuth keys in server env — fill .env.prod.oauth then redeploy.",
            doc="docs/OPERATOR_SOCIAL_OAUTH_SETUP.md",
            commands=[
                "MERGE=1 ./scripts/operator-oauth-env-init.sh",
                "./scripts/operator-social-oauth-prep-all.sh",
                "./scripts/operator-oauth-register-guide.sh",
                "REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh",
            ],
            ui_link="/integrations?tab=hub",
            step_id="oauth_env",
        )

    if social_oauth and social_oauth.active_channel_count == 0:
        return OperatorNextActionOut(
            title="Connect social OAuth",
            why="Keys present but no channel connected — Marketplace → Install → Hub → Connect.",
            doc="docs/OPERATOR_FIRST_LIVE_POST.md",
            commands=[
                "./scripts/operator-social-oauth-status.sh",
                "./scripts/operator-oauth-register-guide.sh",
            ],
            ui_link="/integrations?tab=hub",
            step_id="oauth_connect",
        )

    if first and first.id in {"publish_queue", "publish_media"}:
        return OperatorNextActionOut(
            title=first.label,
            why=first.detail,
            doc="docs/OPERATOR_FIRST_LIVE_POST.md",
            commands=["./scripts/operator-publish-lane-prep.sh"],
            ui_link=first.link,
            step_id=first.id,
        )

    if first and first.id == "simulate_publish":
        return OperatorNextActionOut(
            title="Run social simulate",
            why=first.detail,
            doc="docs/OPERATOR_FIRST_LIVE_POST.md",
            commands=[
                "RUN_SIMULATE=1 ./scripts/operator-publish-simulate-gate.sh",
            ],
            ui_link="/integrations?tab=studio#social-publish",
            step_id=first.id,
        )

    if not settings.social_publish_live_enabled:
        return OperatorNextActionOut(
            title="Enable live publish (kill switch)",
            why="Simulate path ready — set SOCIAL_PUBLISH_LIVE_ENABLED=true after OAuth review.",
            doc="docs/OPERATOR_FIRST_LIVE_POST.md",
            commands=[
                "./scripts/operator-live-publish-prep.sh",
                "APPLY=1 ./scripts/operator-live-publish-prep.sh",
            ],
            ui_link="/integrations?tab=studio#social-publish",
            step_id="live_flag",
        )

    if first and first.id == "first_live_post":
        return OperatorNextActionOut(
            title="First live post",
            why=first.detail,
            doc="docs/OPERATOR_FIRST_LIVE_POST.md",
            commands=[
                "./scripts/operator-live-publish-gate.sh",
                "RUN_LIVE=1 ./scripts/operator-live-publish-gate.sh",
            ],
            ui_link="/integrations?tab=studio#social-publish",
            step_id=first.id,
        )

    if first and first.id == "trusted_auto":
        return OperatorNextActionOut(
            title="Optional: trusted auto-publish",
            why=first.detail,
            doc="docs/OPERATOR_PUBLISH_LANE_MANUAL.md",
            commands=["# SOCIAL_PUBLISH_TRUSTED_AUTO_ENABLED=true after manual simulates"],
            ui_link="/settings/harness#operator-hub",
            step_id=first.id,
        )

    progress = publish_onboarding.progress_pct
    return OperatorNextActionOut(
        title="Publish lane complete — app walkthrough",
        why=f"Onboarding {progress}% — run full operator audit and UI walkthrough.",
        doc="docs/AUTHENTICATED_PROD_WALKTHROUGH.md",
        commands=[
            "./scripts/operator-full-app-audit.sh",
            "./scripts/operator-release-gate.sh",
        ],
        ui_link="/settings/harness#operator-hub",
        step_id="walkthrough",
    )


__all__ = ["OperatorNextActionOut", "resolve_operator_next_action"]
