"""Unit tests for supervisor session audit digest helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.application.services.supervisor.session_audit_digest import build_supervisor_audit_digest_markdown


def test_build_supervisor_audit_digest_markdown_includes_counts() -> None:
    """Digest markdown summarizes action counts and sessions."""

    now = datetime(2026, 5, 19, 7, 0, tzinfo=UTC)
    rows = [
        SimpleNamespace(
            action="supervisor_session_control",
            target_ref="sess-1",
            created_at=now,
            payload={"control_action": "resume"},
        ),
        SimpleNamespace(
            action="supervisor_session_review",
            target_ref="sess-1",
            created_at=now,
            payload={"decision": "approve"},
        ),
    ]
    body = build_supervisor_audit_digest_markdown(
        tenant_name="Acme Hive",
        window_hours=24,
        rows=rows,  # type: ignore[arg-type]
        generated_at=now,
    )
    assert "supervisor_session_control" in body
    assert "supervisor_session_review" in body
    assert "sess-1" in body


def test_build_supervisor_audit_digest_slack_text_is_compact() -> None:
    """Slack digest text includes counts without markdown report headers."""

    now = datetime(2026, 5, 19, 7, 0, tzinfo=UTC)
    rows = [
        SimpleNamespace(action="supervisor_session_control", target_ref="sess-1", created_at=now, payload={}),
    ]
    from app.application.services.supervisor.session_audit_digest import build_supervisor_audit_digest_slack_text

    text = build_supervisor_audit_digest_slack_text(
        tenant_name="Acme Hive",
        window_hours=24,
        rows=rows,  # type: ignore[arg-type]
        generated_at=now,
    )
    assert "Supervisor audit digest" in text
    assert "supervisor_session_control" in text
    assert "## Action counts" not in text


@pytest.mark.asyncio
async def test_send_supervisor_audit_digest_slack_when_disabled_then_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slack digest helper skips when feature flag is off."""

    from app.application.services.supervisor.session_audit_digest import send_supervisor_audit_digest_slack
    from app.core.config import settings

    monkeypatch.setattr(settings, "supervisor_audit_digest_slack_enabled", False)
    ok = await send_supervisor_audit_digest_slack(
        tenant_name="Acme",
        window_hours=24,
        rows=[],
        generated_at=datetime.now(tz=UTC),
    )
    assert ok is False


@pytest.mark.asyncio
async def test_run_supervisor_audit_digest_tick_skips_non_due_tenants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hourly tick skips tenants that are not due at the current hour."""

    import uuid
    from types import SimpleNamespace

    from app.application.services.supervisor import session_audit_digest as digest_mod
    from app.application.services.supervisor.session_audit_digest import run_supervisor_audit_digest_tick
    from app.core.config import settings

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        status="active",
        operator_settings={"supervisor_audit_digest": {"enabled": True, "schedule_hour_utc": 3}},
    )

    class _FakeDb:
        async def scalars(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
            class _Result:
                def all(self) -> list[object]:
                    return [tenant]

            return _Result()

    monkeypatch.setattr(settings, "supervisor_audit_digest_enabled", True)
    monkeypatch.setattr(digest_mod, "is_tenant_digest_due", lambda **_kwargs: False)

    payload = await run_supervisor_audit_digest_tick(_FakeDb())  # type: ignore[arg-type]
    assert payload["tenants_processed"] == 0
    assert payload["tenants_skipped"] == 1
