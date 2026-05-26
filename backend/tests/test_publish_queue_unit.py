"""Unit tests for Publish Queue Phase B classification and review tags."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.application.services.publish_queue import (
    TAG_PUBLISH_QUEUE_APPROVED,
    TAG_PUBLISH_QUEUE_REJECTED,
    apply_publish_queue_review_tags,
    classify_publish_queue_status,
)
from app.application.services.publish_pack import (
    TAG_PUBLISH_PACK_VERIFIED,
    TAG_READY_TO_PUBLISH,
    TAG_SIMULATE_ONLY,
)
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable


def _row(*, tags: list[str], structured: dict | None = None) -> TaskFinalDeliverable:
    return TaskFinalDeliverable(
        id=uuid.uuid4(),
        lineage_id=uuid.uuid4(),
        version=1,
        title="Launch post",
        slug="launch-post",
        markdown_body="# Launch",
        structured_json=structured or {"body": "Hello world", "channel": "instagram", "simulate_only": True},
        tags=tags,
        archive_relpath="x.md",
        chroma_embedding_id="emb",
        dashboard_user_id=uuid.uuid4(),
        created_at=datetime.now(tz=UTC),
    )


def test_classify_publish_queue_status_pending() -> None:
    row = _row(tags=[TAG_PUBLISH_PACK_VERIFIED, TAG_SIMULATE_ONLY, TAG_READY_TO_PUBLISH, "publish_pack"])
    assert classify_publish_queue_status(row) == "pending"


def test_classify_publish_queue_status_approved() -> None:
    row = _row(tags=[TAG_PUBLISH_PACK_VERIFIED, TAG_SIMULATE_ONLY, TAG_PUBLISH_QUEUE_APPROVED])
    assert classify_publish_queue_status(row) == "approved"


def test_classify_publish_queue_status_rejected() -> None:
    row = _row(tags=[TAG_PUBLISH_PACK_VERIFIED, TAG_SIMULATE_ONLY, TAG_PUBLISH_QUEUE_REJECTED])
    assert classify_publish_queue_status(row) == "rejected"


def test_classify_publish_queue_status_non_candidate() -> None:
    row = _row(tags=["draft"])
    assert classify_publish_queue_status(row) is None


def test_apply_publish_queue_review_tags_approve() -> None:
    updated = apply_publish_queue_review_tags(
        [TAG_PUBLISH_PACK_VERIFIED, TAG_SIMULATE_ONLY, TAG_READY_TO_PUBLISH],
        decision="approve",
    )
    assert TAG_PUBLISH_QUEUE_APPROVED in updated
    assert TAG_READY_TO_PUBLISH not in updated


def test_apply_publish_queue_review_tags_reject() -> None:
    updated = apply_publish_queue_review_tags(
        [TAG_PUBLISH_PACK_VERIFIED, TAG_SIMULATE_ONLY, TAG_READY_TO_PUBLISH],
        decision="reject",
    )
    assert TAG_PUBLISH_QUEUE_REJECTED in updated
    assert TAG_PUBLISH_QUEUE_APPROVED not in updated
