"""Unit tests for social publish multi-target pipeline helpers."""

from __future__ import annotations

import uuid

from app.application.services.social_publish_pipeline import (
    SocialPublishPipelineTargetIn,
    build_pipeline_rollback_receipt,
    normalize_pipeline_targets,
)


def test_normalize_pipeline_targets_deduplicates_channel_order() -> None:
    targets = normalize_pipeline_targets(
        [
            SocialPublishPipelineTargetIn(channel="twitter"),
            SocialPublishPipelineTargetIn(channel="instagram"),
            SocialPublishPipelineTargetIn(channel="twitter"),
        ],
    )
    assert [row.channel for row in targets] == ["twitter", "instagram"]


def test_normalize_pipeline_targets_raises_when_empty() -> None:
    try:
        normalize_pipeline_targets([])
    except ValueError as exc:
        assert "At least one target channel is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty target list")


def test_build_pipeline_rollback_receipt_extracts_upstream_reference() -> None:
    deliverable_id = uuid.uuid4()
    receipt = build_pipeline_rollback_receipt(
        deliverable_id=deliverable_id,
        channel="twitter",
        upstream={"tweet_id": "190001"},
    )
    assert receipt.deliverable_id == str(deliverable_id)
    assert receipt.channel == "twitter"
    assert receipt.strategy == "compensating_post"
    assert receipt.upstream_ref == "190001"
