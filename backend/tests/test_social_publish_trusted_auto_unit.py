"""Unit tests for Phase G trusted auto-publish policy."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.application.services.social_publish import TAG_SOCIAL_PUBLISH_SIMULATED
from app.application.services.social_publish_trusted_auto import (
    TrustedAutoPolicyPatch,
    build_trusted_auto_policy,
    deliverable_was_simulated,
    merge_trusted_auto_patch,
    resolve_trusted_auto_live_confirmation,
)


def test_deliverable_was_simulated() -> None:
    assert deliverable_was_simulated([TAG_SOCIAL_PUBLISH_SIMULATED]) is True
    assert deliverable_was_simulated(["publish-queue-approved"]) is False


def test_merge_trusted_auto_patch_persists_channels() -> None:
    merged = merge_trusted_auto_patch(
        {},
        TrustedAutoPolicyPatch(enabled=True, min_simulates=3, channels={"instagram": "auto", "twitter": "manual"}),
    )
    bucket = merged["publish_lane"]["trusted_auto"]
    assert bucket["enabled"] is True
    assert bucket["min_simulates"] == 3
    assert bucket["channels"]["instagram"] == "auto"
    assert bucket["channels"]["twitter"] == "manual"


def test_resolve_trusted_auto_manual_confirm_wins() -> None:
    row = SimpleNamespace(tags=[TAG_SOCIAL_PUBLISH_SIMULATED])
    tenant = SimpleNamespace(operator_settings={"publish_lane": {"trusted_auto": {"enabled": False}}})
    ok, reason = resolve_trusted_auto_live_confirmation(
        tenant=tenant,
        channel="instagram",
        operator_confirmed=True,
        row=row,
    )
    assert ok is True
    assert reason == "manual_confirm"


@pytest.mark.parametrize(
    ("global_on", "tenant_on", "mode", "sim_count", "pack_simulated", "expected_ok", "expected_reason"),
    [
        (False, True, "auto", 10, True, False, "trusted_auto_global_off"),
        (True, False, "auto", 10, True, False, "trusted_auto_tenant_off"),
        (True, True, "manual", 10, True, False, "channel_manual_mode"),
        (True, True, "auto", 2, True, False, "insufficient_channel_simulates"),
        (True, True, "auto", 10, False, False, "pack_not_simulated"),
        (True, True, "auto", 10, True, True, "trusted_auto"),
    ],
)
def test_resolve_trusted_auto_live_confirmation_matrix(
    global_on: bool,
    tenant_on: bool,
    mode: str,
    sim_count: int,
    pack_simulated: bool,
    expected_ok: bool,
    expected_reason: str,
) -> None:
    tags = [TAG_SOCIAL_PUBLISH_SIMULATED] if pack_simulated else []
    row = SimpleNamespace(tags=tags)
    tenant = SimpleNamespace(
        operator_settings={
            "publish_lane": {
                "trusted_auto": {
                    "enabled": tenant_on,
                    "min_simulates": 5,
                    "channels": {"instagram": mode},
                },
            },
        },
    )
    with (
        patch("app.application.services.social_publish_trusted_auto.settings") as mock_settings,
        patch(
            "app.application.services.social_publish_trusted_auto.count_successful_channel_simulates",
            return_value=sim_count,
        ),
    ):
        mock_settings.social_publish_trusted_auto_enabled = global_on
        mock_settings.social_publish_live_enabled = True
        mock_settings.social_publish_trusted_auto_min_simulates = 5
        ok, reason = resolve_trusted_auto_live_confirmation(
            tenant=tenant,
            channel="instagram",
            operator_confirmed=False,
            row=row,
        )
    assert ok is expected_ok
    assert reason == expected_reason


def test_build_trusted_auto_policy_marks_eligible_channel() -> None:
    tenant = SimpleNamespace(
        operator_settings={
            "publish_lane": {
                "trusted_auto": {
                    "enabled": True,
                    "channels": {"instagram": "auto"},
                },
            },
        },
    )
    with (
        patch("app.application.services.social_publish_trusted_auto.settings") as mock_settings,
        patch(
            "app.application.services.social_publish_trusted_auto.count_successful_channel_simulates",
            return_value=7,
        ),
    ):
        mock_settings.social_publish_trusted_auto_enabled = True
        mock_settings.social_publish_live_enabled = True
        mock_settings.social_publish_trusted_auto_min_simulates = 5
        policy = build_trusted_auto_policy(tenant)

    ig = next(row for row in policy.channels if row.channel == "instagram")
    assert policy.tenant_enabled is True
    assert ig.mode == "auto"
    assert ig.successful_simulates == 7
    assert ig.auto_eligible is True
