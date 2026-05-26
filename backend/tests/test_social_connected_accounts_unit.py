"""Unit tests for multi-account social connected accounts service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.social_connected_accounts import (
    publish_context_from_account,
    resolve_social_account_for_publish,
)
from app.infrastructure.persistence.models.social_connected_account import SocialConnectedAccount


def _account_row(
    *,
    channel: str = "twitter",
    account_id: uuid.UUID | None = None,
    is_default: bool = False,
) -> SocialConnectedAccount:
    row = SocialConnectedAccount(
        tenant_id=uuid.uuid4(),
        dashboard_user_id=uuid.uuid4(),
        channel=channel,
        account_key="x:123",
        label="@queenswarm",
        oauth_provider_key="twitter_api_v2",
        connector_slug="twitter_api_v2",
        secrets_cipher="cipher",
        is_default=is_default,
    )
    row.id = account_id or uuid.uuid4()
    row.profile_meta = {"user_id": "123", "username": "queenswarm"}
    return row


def test_publish_context_from_account_maps_profile_meta() -> None:
    row = _account_row(channel="instagram")
    row.profile_meta = {"ig_user_id": "1789", "page_id": "999"}
    ctx = publish_context_from_account(row)
    assert ctx["ig_user_id"] == "1789"
    assert ctx["page_id"] == "999"


@pytest.mark.asyncio
async def test_resolve_social_account_prefers_explicit_id(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.operator_settings = {}

    explicit = _account_row(account_id=uuid.uuid4())
    default = _account_row(account_id=uuid.uuid4(), is_default=True)

    async def _get(session, *, tenant_id, account_id):  # noqa: ANN001
        if account_id == explicit.id:
            return explicit
        return None

    async def _list(session, *, tenant_id, channel, active_only=True):  # noqa: ANN001, ARG001
        return [default]

    monkeypatch.setattr(
        "app.application.services.social_connected_accounts.get_social_account",
        _get,
    )
    monkeypatch.setattr(
        "app.application.services.social_connected_accounts.list_social_accounts",
        _list,
    )

    resolved = await resolve_social_account_for_publish(
        AsyncMock(),
        tenant=tenant,
        channel="twitter",
        account_id=explicit.id,
        structured={},
    )
    assert resolved is explicit


@pytest.mark.asyncio
async def test_resolve_social_account_from_publish_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.operator_settings = {}

    pack_account = _account_row(account_id=uuid.uuid4())

    async def _get(session, *, tenant_id, account_id):  # noqa: ANN001
        if account_id == pack_account.id:
            return pack_account
        return None

    async def _list(session, *, tenant_id, channel, active_only=True):  # noqa: ANN001, ARG001
        return []

    monkeypatch.setattr(
        "app.application.services.social_connected_accounts.get_social_account",
        _get,
    )
    monkeypatch.setattr(
        "app.application.services.social_connected_accounts.list_social_accounts",
        _list,
    )

    resolved = await resolve_social_account_for_publish(
        AsyncMock(),
        tenant=tenant,
        channel="twitter",
        account_id=None,
        structured={"social_account_id": str(pack_account.id)},
    )
    assert resolved is pack_account
