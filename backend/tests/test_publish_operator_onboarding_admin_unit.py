"""Unit tests for publish lane admin onboarding overview."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.services.publish_operator_onboarding_admin import (
    compose_publish_onboarding_admin_overview,
)


@pytest.mark.asyncio
async def test_compose_publish_onboarding_admin_overview(monkeypatch) -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    tenant = SimpleNamespace(id=tenant_id, slug="acme", name="Acme Hive")

    class _FakeResult:
        def all(self):  # noqa: ANN204
            return [tenant]

    async def _fake_scalars(_query):  # noqa: ANN001
        return _FakeResult()

    async def _fake_scalar(_query):  # noqa: ANN001
        return SimpleNamespace(dashboard_user_id=user_id)

    async def _fake_snapshot(_session, *, tenant_id, dashboard_user_id, tenant=None):  # noqa: ANN001, ARG001
        step = SimpleNamespace(status="done")
        return SimpleNamespace(
            progress_pct=50,
            steps=[step, SimpleNamespace(status="pending")],
            flags={"brain_pack_done": True},
        )

    session = SimpleNamespace(scalars=_fake_scalars, scalar=_fake_scalar)
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding_admin.compose_publish_onboarding_snapshot",
        _fake_snapshot,
    )

    overview = await compose_publish_onboarding_admin_overview(session, limit=10)
    assert overview.tenant_count == 1
    assert overview.tenants[0].tenant_slug == "acme"
    assert overview.tenants[0].progress_pct == 50
    assert overview.average_progress_pct == 50
