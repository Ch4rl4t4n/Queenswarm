"""Unit coverage for tenancy slug + audit payload helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.tenancy import _slugify, enrich_audit_payload, ensure_default_tenant_for_user


def test_slugify_normalizes_and_truncates() -> None:
    assert _slugify("  Hello World!!  ") == "hello-world"
    assert _slugify("!!!") == "tenant"


@pytest.mark.asyncio
async def test_ensure_default_tenant_returns_existing_membership() -> None:
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id)
    membership = SimpleNamespace(tenant_id=tenant_id)
    user = SimpleNamespace(id=uuid.uuid4(), active_tenant_id=None, display_name="Op", email="op@x.com", is_admin=False)

    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[membership])))
    db.get = AsyncMock(return_value=tenant)
    db.flush = AsyncMock()

    found = await ensure_default_tenant_for_user(db, user=user)

    assert found is tenant
    assert user.active_tenant_id == tenant_id


def test_enrich_audit_payload_adds_client_ip() -> None:
    payload = enrich_audit_payload({"action": "login"}, client_ip="10.0.0.1")
    assert payload["ip"] == "10.0.0.1"
    assert payload["action"] == "login"
