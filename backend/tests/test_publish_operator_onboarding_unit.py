"""Unit tests for publish lane operator onboarding snapshot."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.services.publish_operator_onboarding import compose_publish_onboarding_snapshot
from app.domain.memory.curated import CuratedFileKind


@pytest.mark.asyncio
async def test_compose_publish_onboarding_all_pending(monkeypatch) -> None:
    """Empty tenant yields low progress and pending steps."""

    tenant_id = uuid4()
    user_id = uuid4()

    async def _fake_bundle(_tenant_id):  # noqa: ANN001
        return {kind: "" for kind in CuratedFileKind}

    async def _fake_trio(_db, *, tenant_id):  # noqa: ANN001, ARG001
        return {"lanes_bound": 0, "lanes_total": 3, "lanes": []}

    async def _fake_social(_session, *, dashboard_user_id, tenant=None, limit=20):  # noqa: ANN001, ARG001
        return SimpleNamespace(
            channels=[],
            ready_items=[],
            links={"marketplace": "/integrations?tab=marketplace"},
        )

    class _FakeSvc:
        async def fetch_by_slug(self, _session, *, slug):  # noqa: ANN001, ARG002
            return None

    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.CuratedMemoryService",
        lambda db: SimpleNamespace(get_bundle=_fake_bundle),
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.get_solo_trio_status",
        _fake_trio,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_social_publish_snapshot",
        _fake_social,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_publish_audit_snapshot",
        lambda _tenant, limit=20: SimpleNamespace(entries=[]),
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_trusted_auto_policy",
        lambda _tenant: SimpleNamespace(tenant_enabled=False, channels=[]),
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.DynamicConnectorService",
        _FakeSvc,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.settings",
        SimpleNamespace(
            social_publish_enabled=True,
            social_publish_live_enabled=False,
            social_publish_trusted_auto_enabled=False,
        ),
    )

    snapshot = await compose_publish_onboarding_snapshot(
        SimpleNamespace(),
        tenant_id=tenant_id,
        dashboard_user_id=user_id,
        tenant=None,
    )

    assert snapshot.progress_pct == 0
    assert snapshot.steps[0].id == "brain_pack"
    assert snapshot.steps[0].status == "pending"
    assert snapshot.flags["live_enabled"] is False
    assert len(snapshot.steps) == 11


@pytest.mark.asyncio
async def test_compose_publish_onboarding_full_complete(monkeypatch) -> None:
    """All checklist steps done yields 100% progress."""

    tenant_id = uuid4()
    user_id = uuid4()
    tenant = SimpleNamespace(id=tenant_id)

    async def _fake_bundle(_tenant_id):  # noqa: ANN001
        return {
            CuratedFileKind.SOUL: "soul text",
            CuratedFileKind.SKILLS_HIERARCHY: "skills",
            CuratedFileKind.MISSION: "mission",
            CuratedFileKind.IDEAL_STATE: "ideal",
            CuratedFileKind.INSTRUCTIONS: "instructions",
        }

    async def _fake_trio(_db, *, tenant_id):  # noqa: ANN001, ARG001
        return {
            "lanes_bound": 3,
            "lanes_total": 3,
            "lanes": [{"last_session_status": "completed"}],
        }

    channel = SimpleNamespace(channel="instagram", credentials_ok=True, active=True)
    ready = SimpleNamespace(media_url="https://cdn.example.com/post.jpg")

    async def _fake_social(_session, *, dashboard_user_id, tenant=None, limit=20):  # noqa: ANN001, ARG001
        return SimpleNamespace(channels=[channel], ready_items=[ready], links={})

    class _FakeSvc:
        async def fetch_by_slug(self, _session, *, slug):  # noqa: ANN001, ARG002
            return SimpleNamespace(is_active=True)

    def _audit(_tenant, limit=20):  # noqa: ANN001, ARG002
        return SimpleNamespace(
            entries=[
                SimpleNamespace(kind="social_simulate", ok=True),
                SimpleNamespace(kind="social_live", ok=True),
            ],
        )

    auto_channel = SimpleNamespace(channel="instagram", auto_eligible=True)

    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.CuratedMemoryService",
        lambda db: SimpleNamespace(get_bundle=_fake_bundle),
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.get_solo_trio_status",
        _fake_trio,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_social_publish_snapshot",
        _fake_social,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_publish_audit_snapshot",
        _audit,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_trusted_auto_policy",
        lambda _tenant: SimpleNamespace(tenant_enabled=True, channels=[auto_channel]),
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.DynamicConnectorService",
        _FakeSvc,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.settings",
        SimpleNamespace(
            social_publish_enabled=True,
            social_publish_live_enabled=True,
            social_publish_trusted_auto_enabled=True,
        ),
    )

    snapshot = await compose_publish_onboarding_snapshot(
        SimpleNamespace(),
        tenant_id=tenant_id,
        dashboard_user_id=user_id,
        tenant=tenant,
    )

    assert snapshot.progress_pct == 100
    assert all(step.status == "done" for step in snapshot.steps)


@pytest.mark.asyncio
async def test_compose_publish_onboarding_gmail_not_social_oauth(monkeypatch) -> None:
    """Gmail/newsletter connector must not satisfy social OAuth checklist step."""

    tenant_id = uuid4()
    user_id = uuid4()

    async def _fake_bundle(_tenant_id):  # noqa: ANN001
        return {kind: "x" for kind in CuratedFileKind}

    async def _fake_trio(_db, *, tenant_id):  # noqa: ANN001, ARG001
        return {"lanes_bound": 3, "lanes_total": 3, "lanes": [{"last_session_status": "completed"}]}

    gmail = SimpleNamespace(channel="newsletter", credentials_ok=True, active=True)

    async def _fake_social(_session, *, dashboard_user_id, tenant=None, limit=20):  # noqa: ANN001, ARG001
        return SimpleNamespace(channels=[gmail], ready_items=[], links={})

    class _FakeSvc:
        async def fetch_by_slug(self, _session, *, slug):  # noqa: ANN001, ARG002
            return None

    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.CuratedMemoryService",
        lambda db: SimpleNamespace(get_bundle=_fake_bundle),
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.get_solo_trio_status",
        _fake_trio,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_social_publish_snapshot",
        _fake_social,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_publish_audit_snapshot",
        lambda _tenant, limit=20: SimpleNamespace(entries=[]),
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.build_trusted_auto_policy",
        lambda _tenant: SimpleNamespace(tenant_enabled=False, channels=[]),
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.DynamicConnectorService",
        _FakeSvc,
    )
    monkeypatch.setattr(
        "app.application.services.publish_operator_onboarding.settings",
        SimpleNamespace(
            social_publish_enabled=True,
            social_publish_live_enabled=False,
            social_publish_trusted_auto_enabled=False,
        ),
    )

    snapshot = await compose_publish_onboarding_snapshot(
        SimpleNamespace(),
        tenant_id=tenant_id,
        dashboard_user_id=user_id,
        tenant=None,
    )

    oauth_step = next(step for step in snapshot.steps if step.id == "social_oauth")
    assert oauth_step.status == "pending"
    assert snapshot.flags["social_oauth_done"] is False
