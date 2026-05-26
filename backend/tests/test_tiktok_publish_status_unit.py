"""Unit tests for TikTok publish status polling."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.services.tiktok_publish_status import (
    extract_tiktok_publish_id,
    poll_tiktok_publish_status,
)


def test_extract_tiktok_publish_id_from_json_result() -> None:
    upstream = {
        "ok": True,
        "result": json.dumps({"data": {"publish_id": "pub_abc123"}}),
    }
    assert extract_tiktok_publish_id(upstream) == "pub_abc123"


def test_extract_tiktok_publish_id_from_simulated() -> None:
    upstream = {"simulated_result": {"publish_id": "sim_pub_1"}}
    assert extract_tiktok_publish_id(upstream) == "sim_pub_1"


@pytest.mark.asyncio
async def test_poll_tiktok_simulate_skips_upstream() -> None:
    with patch(
        "app.application.services.tiktok_publish_status.execute_studio_tool",
        new_callable=AsyncMock,
    ) as mock_exec:
        out = await poll_tiktok_publish_status(
            AsyncMock(),
            dashboard_user_id=uuid4(),
            tenant=None,
            publish_id="pub_test",
            mode="simulate",
            operator_confirmed=False,
        )
    mock_exec.assert_not_called()
    assert out.status == "simulated"


@pytest.mark.asyncio
async def test_poll_tiktok_live_published_on_success() -> None:
    success_payload = json.dumps({"data": {"status": "PUBLISH_COMPLETE"}})

    with patch(
        "app.application.services.tiktok_publish_status.execute_studio_tool",
        new_callable=AsyncMock,
        return_value={"ok": True, "result": success_payload},
    ):
        out = await poll_tiktok_publish_status(
            AsyncMock(),
            dashboard_user_id=uuid4(),
            tenant=None,
            publish_id="pub_live",
            mode="live",
            operator_confirmed=True,
        )
    assert out.status == "published"
    assert out.attempts == 1
