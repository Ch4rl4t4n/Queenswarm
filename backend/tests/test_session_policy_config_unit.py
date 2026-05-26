"""Unit tests for tenant session policy config."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.session_policy_config import (
    merge_tenant_session_policy_patch,
    resolve_effective_session_policy,
    serialize_session_policy_view,
)


def test_resolve_effective_session_policy_uses_deployment_by_default() -> None:
    tenant = SimpleNamespace(id="t1", operator_settings={})
    effective = resolve_effective_session_policy(tenant)  # type: ignore[arg-type]
    assert "access_token_expire_minutes" in effective
    assert "refresh_token_expire_days" in effective
    assert effective["oauth_pkce_enabled"] is True


def test_tenant_override_access_and_refresh_ttl() -> None:
    tenant = SimpleNamespace(
        id="t2",
        operator_settings={
            "session_policy": {
                "access_token_source": "tenant",
                "access_token_minutes": 30,
                "refresh_token_source": "tenant",
                "refresh_token_days": 7,
            },
        },
    )
    effective = resolve_effective_session_policy(tenant)  # type: ignore[arg-type]
    assert effective["access_token_expire_minutes"] == 30
    assert effective["refresh_token_expire_days"] == 7


def test_serialize_session_policy_view_marks_editable() -> None:
    tenant = SimpleNamespace(id="t3", operator_settings={})
    view = serialize_session_policy_view(tenant, editable=True)  # type: ignore[arg-type]
    assert view["editable"] is True
    assert view["access_token_source"] == "deployment"


def test_merge_tenant_session_policy_patch_persists_rate_limit() -> None:
    tenant = SimpleNamespace(id="t4", operator_settings={})
    root = merge_tenant_session_policy_patch(
        tenant,  # type: ignore[arg-type]
        rate_limit_source="tenant",
        rate_limit_enabled=True,
        rate_limit_requests=1200,
        rate_limit_window_sec=60.0,
    )
    bucket = root["session_policy"]
    assert bucket["rate_limit_source"] == "tenant"
    assert bucket["rate_limit_requests"] == 1200


@pytest.mark.asyncio
async def test_cache_tenant_rate_limits_writes_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import session_policy_config as mod

    captured: dict[str, object] = {}

    async def fake_set_json(key: str, value: object, ttl: int | None = None) -> None:
        captured["key"] = key
        captured["value"] = value
        captured["ttl"] = ttl

    monkeypatch.setattr(mod, "set_json", fake_set_json)
    tenant = SimpleNamespace(
        operator_settings={
            "session_policy": {
                "rate_limit_source": "tenant",
                "rate_limit_enabled": True,
                "rate_limit_requests": 180,
                "rate_limit_window_sec": 90.0,
            }
        }
    )
    tenant_id = uuid.uuid4()
    await mod.cache_tenant_rate_limits(tenant_id, tenant=tenant)  # type: ignore[arg-type]
    assert str(captured["key"]).endswith(str(tenant_id))
    assert captured["value"] == {"enabled": True, "requests": 180, "window_sec": 90.0}
