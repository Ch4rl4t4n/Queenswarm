"""Trusted auto-publish — Phase G manual vs auto live after N successful simulates."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.execution_studio_activity import list_execution_activity
from app.application.services.social_publish import (
    SOCIAL_OAUTH_CHANNEL_IDS,
    SocialChannelId,
    TAG_SOCIAL_PUBLISH_SIMULATED,
)
from app.core.config import settings
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.infrastructure.persistence.models.tenant import Tenant

PublishMode = Literal["manual", "auto"]

PUBLISH_LANE_SETTINGS_KEY = "publish_lane"
TRUSTED_AUTO_BUCKET_KEY = "trusted_auto"

DEFAULT_CHANNEL_MODES: dict[str, PublishMode] = {channel: "manual" for channel in SOCIAL_OAUTH_CHANNEL_IDS}


class TrustedAutoChannelOut(BaseModel):
    """Per-channel trusted auto status for operator UI."""

    model_config = ConfigDict(extra="ignore")

    channel: SocialChannelId
    mode: PublishMode = "manual"
    successful_simulates: int = 0
    min_simulates_required: int = 5
    auto_eligible: bool = False


class TrustedAutoPolicyOut(BaseModel):
    """Tenant trusted auto-publish policy snapshot."""

    model_config = ConfigDict(extra="ignore")

    global_enabled: bool = False
    tenant_enabled: bool = False
    min_simulates_required: int = 5
    live_enabled: bool = False
    channels: list[TrustedAutoChannelOut] = Field(default_factory=list)


class TrustedAutoPolicyPatch(BaseModel):
    """Partial patch for trusted auto policy (tenant operator_settings)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    min_simulates: int | None = Field(default=None, ge=1, le=100)
    channels: dict[str, PublishMode] | None = None


def _publish_lane_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    lane = dict(root.get(PUBLISH_LANE_SETTINGS_KEY) or {})
    if not isinstance(lane, dict):
        lane = {}
    return lane


def _trusted_auto_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    lane = _publish_lane_bucket(operator_settings)
    bucket = dict(lane.get(TRUSTED_AUTO_BUCKET_KEY) or {})
    return bucket if isinstance(bucket, dict) else {}


def merge_trusted_auto_patch(operator_settings: dict[str, Any] | None, patch: TrustedAutoPolicyPatch) -> dict[str, Any]:
    """Apply trusted auto patch into tenant operator_settings."""

    root = dict(operator_settings or {})
    lane = _publish_lane_bucket(root)
    bucket = _trusted_auto_bucket(root)

    if patch.enabled is not None:
        bucket["enabled"] = bool(patch.enabled)
    if patch.min_simulates is not None:
        bucket["min_simulates"] = int(patch.min_simulates)
    if patch.channels is not None:
        normalized: dict[str, str] = dict(bucket.get("channels") or {})
        for raw_key, mode in patch.channels.items():
            key = str(raw_key).strip().lower()
            if key in SOCIAL_OAUTH_CHANNEL_IDS and mode in {"manual", "auto"}:
                normalized[key] = mode
        bucket["channels"] = normalized

    lane[TRUSTED_AUTO_BUCKET_KEY] = bucket
    root[PUBLISH_LANE_SETTINGS_KEY] = lane
    return root


def _min_simulates_required(bucket: dict[str, Any]) -> int:
    override = bucket.get("min_simulates")
    if isinstance(override, int) and override >= 1:
        return min(override, 100)
    return int(settings.social_publish_trusted_auto_min_simulates)


def count_successful_channel_simulates(tenant: Tenant | None, *, channel: SocialChannelId) -> int:
    """Count ok social simulate audit events for a channel on this tenant."""

    if tenant is None:
        return 0
    total = 0
    for row in list_execution_activity(tenant, limit=120):
        event_type = str(row.get("event_type") or "")
        if event_type != "publish_social_simulate":
            continue
        payload = dict(row.get("payload") or {})
        if payload.get("ok") is not True:
            continue
        if str(payload.get("channel") or "").strip().lower() != channel:
            continue
        total += 1
    return total


def channel_publish_mode(bucket: dict[str, Any], channel: SocialChannelId) -> PublishMode:
    """Resolve manual/auto mode for one channel."""

    channels = bucket.get("channels")
    if isinstance(channels, dict):
        raw = str(channels.get(channel) or "manual").strip().lower()
        if raw == "auto":
            return "auto"
    return "manual"


def deliverable_was_simulated(tags: list[str] | None) -> bool:
    """Return True when this pack already passed social simulate."""

    lowered = {str(tag).lower() for tag in tags or []}
    return TAG_SOCIAL_PUBLISH_SIMULATED.lower() in lowered


def build_trusted_auto_policy(tenant: Tenant | None) -> TrustedAutoPolicyOut:
    """Build trusted auto snapshot for Social publish panel."""

    bucket = _trusted_auto_bucket(tenant.operator_settings if tenant is not None else None)
    min_required = _min_simulates_required(bucket)
    tenant_enabled = bool(bucket.get("enabled"))
    global_on = bool(settings.social_publish_trusted_auto_enabled)

    channels: list[TrustedAutoChannelOut] = []
    for channel_id in sorted(SOCIAL_OAUTH_CHANNEL_IDS):
        sim_count = count_successful_channel_simulates(tenant, channel=channel_id)
        mode = channel_publish_mode(bucket, channel_id)
        eligible = (
            global_on
            and tenant_enabled
            and settings.social_publish_live_enabled
            and mode == "auto"
            and sim_count >= min_required
        )
        channels.append(
            TrustedAutoChannelOut(
                channel=channel_id,
                mode=mode,
                successful_simulates=sim_count,
                min_simulates_required=min_required,
                auto_eligible=eligible,
            ),
        )

    return TrustedAutoPolicyOut(
        global_enabled=global_on,
        tenant_enabled=tenant_enabled,
        min_simulates_required=min_required,
        live_enabled=bool(settings.social_publish_live_enabled),
        channels=channels,
    )


def resolve_trusted_auto_live_confirmation(
    *,
    tenant: Tenant | None,
    channel: SocialChannelId,
    operator_confirmed: bool,
    row: TaskFinalDeliverable,
) -> tuple[bool, str]:
    """Decide whether live publish may proceed without manual operator_confirmed.

    Returns:
        (effective_confirmed, reason_code)
    """

    if operator_confirmed:
        return True, "manual_confirm"

    if not settings.social_publish_trusted_auto_enabled:
        return False, "trusted_auto_global_off"

    if not settings.social_publish_live_enabled:
        return False, "live_disabled"

    if tenant is None:
        return False, "tenant_missing"

    bucket = _trusted_auto_bucket(tenant.operator_settings)
    if not bool(bucket.get("enabled")):
        return False, "trusted_auto_tenant_off"

    if channel_publish_mode(bucket, channel) != "auto":
        return False, "channel_manual_mode"

    if not deliverable_was_simulated(list(row.tags or [])):
        return False, "pack_not_simulated"

    min_required = _min_simulates_required(bucket)
    sim_count = count_successful_channel_simulates(tenant, channel=channel)
    if sim_count < min_required:
        return False, "insufficient_channel_simulates"

    return True, "trusted_auto"


__all__ = [
    "PublishMode",
    "TrustedAutoChannelOut",
    "TrustedAutoPolicyOut",
    "TrustedAutoPolicyPatch",
    "build_trusted_auto_policy",
    "channel_publish_mode",
    "count_successful_channel_simulates",
    "deliverable_was_simulated",
    "merge_trusted_auto_patch",
    "resolve_trusted_auto_live_confirmation",
]
