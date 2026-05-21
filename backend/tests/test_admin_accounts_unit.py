"""Unit tests for admin accounts CMS helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.admin_accounts import (
    COMMERCIAL_DEMO_EMAIL,
    mint_bootstrap_password,
)


def test_mint_bootstrap_password_from_env() -> None:
    assert mint_bootstrap_password(env_password="super-secret-123") == "super-secret-123"


def test_mint_bootstrap_password_generates_when_missing() -> None:
    generated = mint_bootstrap_password(env_password="")
    assert len(generated) >= 16


def test_mint_bootstrap_password_rejects_short_env() -> None:
    with pytest.raises(ValueError, match="too short"):
        mint_bootstrap_password(env_password="short")


@pytest.mark.asyncio
async def test_list_admin_account_audit_logs_requires_user(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import admin_accounts as mod

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with pytest.raises(LookupError):
        await mod.list_admin_account_audit_logs(db, user_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_bulk_update_admin_accounts_patches_active(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import admin_accounts as mod

    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    user = MagicMock()
    user.id = user_id
    user.is_active = True
    user.active_tenant_id = tenant_id

    db = AsyncMock()
    db.get = AsyncMock(return_value=user)
    db.scalar = AsyncMock(return_value=None)
    db.flush = AsyncMock()

    audit_mock = AsyncMock()
    monkeypatch.setattr(mod, "write_tenant_audit_log", audit_mock)

    result = await mod.bulk_update_admin_accounts(
        db,
        user_ids=[user_id],
        is_active=False,
        platform_mode=None,
        tier=None,
        actor_user_id=uuid.uuid4(),
    )
    assert result["updated_users"] == 1
    assert user.is_active is False
    audit_mock.assert_awaited_once()


def test_serialize_admin_account_audit_csv_includes_header() -> None:
    from app.application.services.admin_accounts import serialize_admin_account_audit_csv

    csv_text = serialize_admin_account_audit_csv(
        [
            {
                "id": "a1",
                "tenant_id": "t1",
                "action": "admin_account_updated",
                "target_type": "dashboard_user",
                "target_ref": "u1",
                "actor_user_id": "actor-1",
                "created_at": "2026-05-19T12:00:00+00:00",
                "payload": {"is_active": True},
            },
        ],
    )
    assert "id,tenant_id,action" in csv_text
    assert "admin_account_updated" in csv_text
    assert "is_active" in csv_text


def test_serialize_admin_account_audit_json_pretty() -> None:
    from app.application.services.admin_accounts import serialize_admin_account_audit_json

    payload = serialize_admin_account_audit_json([{"id": "a1", "action": "test", "payload": {}}])
    parsed = __import__("json").loads(payload)
    assert parsed[0]["id"] == "a1"


@pytest.mark.asyncio
async def test_get_commercial_demo_status_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import admin_accounts as mod

    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[None, None])
    status = await mod.get_commercial_demo_status(db, admin_user_id=uuid.uuid4())
    assert status["ready"] is False
    assert status["email"] == mod.COMMERCIAL_DEMO_EMAIL


@pytest.mark.asyncio
async def test_ensure_commercial_demo_preview_membership_grants_viewer(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import admin_accounts as mod

    admin_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    admin = MagicMock()
    admin.is_admin = True

    db = AsyncMock()
    db.get = AsyncMock(return_value=admin)
    db.scalar = AsyncMock(return_value=None)
    db.add = MagicMock()
    db.flush = AsyncMock()

    granted = await mod.ensure_commercial_demo_preview_membership(
        db,
        admin_user_id=admin_id,
        tenant_id=tenant_id,
    )
    assert granted is True
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_commercial_demo_preview_membership_skips_non_admin() -> None:
    from app.application.services import admin_accounts as mod

    admin = MagicMock()
    admin.is_admin = False

    db = AsyncMock()
    db.get = AsyncMock(return_value=admin)

    granted = await mod.ensure_commercial_demo_preview_membership(
        db,
        admin_user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
    )
    assert granted is False
