"""Unit tests for multi-tenant supervisor audit digest rollup."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.application.services.supervisor.session_audit_digest_rollup import (
    build_supervisor_audit_digest_rollup,
)


class _FakeExecuteResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _FakeDb:
    def __init__(
        self,
        *,
        tenants: list[object],
        action_rows: list[object],
        session_rows: list[object],
        trend_rows: list[object] | None = None,
    ) -> None:
        self._tenants = tenants
        self._action_rows = action_rows
        self._session_rows = session_rows
        self._trend_rows = trend_rows or []
        self._call = 0

    async def scalars(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
        class _Result:
            def __init__(self, rows: list[object]) -> None:
                self._rows = rows

            def all(self) -> list[object]:
                return self._rows

        return _Result(self._tenants)

    async def execute(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
        self._call += 1
        if self._call == 1:
            return _FakeExecuteResult(self._action_rows)
        if self._call == 2:
            return _FakeExecuteResult(self._session_rows)
        return _FakeExecuteResult(self._trend_rows)


@pytest.mark.asyncio
async def test_build_supervisor_audit_digest_rollup_aggregates_tenants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rollup summarizes per-tenant action counts and global totals."""

    from app.core.config import settings

    monkeypatch.setattr(settings, "supervisor_audit_digest_enabled", True)

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        name="Acme Hive",
        slug="acme",
        status="active",
        platform_mode="internal",
        operator_settings={"supervisor_audit_digest": {"enabled": True}},
    )
    action_row = SimpleNamespace(
        tenant_id=tenant_id,
        action="supervisor_session_control",
        action_count=2,
    )
    session_row = SimpleNamespace(tenant_id=tenant_id, session_count=1)

    payload = await build_supervisor_audit_digest_rollup(
        _FakeDb(tenants=[tenant], action_rows=[action_row], session_rows=[session_row]),  # type: ignore[arg-type]
        window_hours=168,
    )

    assert payload["tenants_active"] == 1
    assert payload["total_actions"] == 2
    assert payload["global_action_counts"]["supervisor_session_control"] == 2
    assert payload["tenants"][0]["tenant_slug"] == "acme"
    assert payload["tenants"][0]["session_count"] == 1
    assert payload["tenants"][0]["digest_health"] == "never_sent"
    assert payload["digest_health_summary"]["never_sent"] == 1
    assert len(payload["daily_trend"]) == 7


@pytest.mark.asyncio
async def test_build_supervisor_audit_digest_rollup_skips_idle_tenants() -> None:
    """Tenants without supervisor audit activity are omitted from the rollup."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        name="Idle",
        slug="idle",
        status="active",
        platform_mode="commercial",
        operator_settings={},
    )
    payload = await build_supervisor_audit_digest_rollup(
        _FakeDb(tenants=[tenant], action_rows=[], session_rows=[]),  # type: ignore[arg-type]
        window_hours=24,
    )
    assert payload["tenants_active"] == 0
    assert payload["total_actions"] == 0
    assert payload["tenants"] == []


def test_fill_supervisor_audit_rollup_daily_trend_zero_fills_gaps() -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        fill_supervisor_audit_rollup_daily_trend,
    )

    start = datetime(2026, 5, 13, tzinfo=UTC)
    series = fill_supervisor_audit_rollup_daily_trend(
        start_day=start,
        day_count=3,
        rows=[("2026-05-14", 4, 2)],
    )
    assert len(series) == 3
    assert series[0]["action_count"] == 0
    assert series[1]["action_count"] == 4
    assert series[1]["tenants_active"] == 2
    assert series[2]["action_count"] == 0


def test_serialize_supervisor_audit_rollup_markdown_includes_tenant_rows() -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        serialize_supervisor_audit_rollup_markdown,
    )

    body = serialize_supervisor_audit_rollup_markdown(
        {
            "generated_at": "2026-05-19T08:00:00+00:00",
            "window_hours": 168,
            "tenants_active": 1,
            "tenants_total": 2,
            "total_actions": 3,
            "global_action_counts": {"supervisor_session_control": 3},
            "digest_health_summary": {"never_sent": 1},
            "tenants": [
                {
                    "tenant_name": "Acme",
                    "tenant_slug": "acme",
                    "platform_mode": "internal",
                    "action_count": 3,
                    "session_count": 1,
                    "digest_enabled": True,
                    "digest_health": "never_sent",
                    "last_digest_sent_at": None,
                    "action_counts": {"supervisor_session_control": 3},
                },
            ],
        },
    )
    assert "Acme" in body
    assert "supervisor_session_control" in body
    assert "Digest delivery health" in body
    assert "Never sent" in body or "never_sent" in body


def test_summarize_digest_health_alerts_when_stale_tenants_exist() -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        summarize_digest_health_alerts,
    )

    alerts = summarize_digest_health_alerts(
        {
            "digest_health_summary": {"stale": 1, "never_sent": 1},
            "tenants": [
                {"tenant_slug": "acme", "digest_health": "stale"},
                {"tenant_slug": "beta", "digest_health": "never_sent"},
                {"tenant_slug": "ok", "digest_health": "healthy"},
            ],
        },
    )
    assert alerts["needs_attention"] is True
    assert alerts["stale_count"] == 1
    assert alerts["never_sent_count"] == 1
    assert len(alerts["attention_tenants"]) == 2


def test_format_digest_health_slack_summary_when_healthy() -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        format_digest_health_slack_summary,
    )

    line = format_digest_health_slack_summary({"digest_health_summary": {"healthy": 2}})
    assert "healthy" in line.lower()


def test_format_digest_health_markdown_section_lists_attention_tenants() -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        format_digest_health_markdown_section,
    )

    section = "\n".join(
        format_digest_health_markdown_section(
            {
                "digest_health_summary": {"stale": 1},
                "tenants": [
                    {
                        "tenant_name": "Acme Hive",
                        "tenant_slug": "acme",
                        "digest_health": "stale",
                        "last_digest_sent_at": "2026-05-01T07:00:00+00:00",
                    },
                ],
            },
        ),
    )
    assert "Hives needing attention" in section
    assert "Acme Hive" in section
    assert "stale" in section


@pytest.mark.asyncio
async def test_send_attention_supervisor_audit_digests_when_no_alerts_then_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        send_attention_supervisor_audit_digests,
    )

    async def _fake_build(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return {"digest_health_summary": {"healthy": 2}, "tenants": []}

    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.build_supervisor_audit_digest_rollup",
        _fake_build,
    )

    result = await send_attention_supervisor_audit_digests(object(), window_hours=168)  # type: ignore[arg-type]
    assert result["sent"] is False
    assert result["reason"] == "no_attention_tenants"
    assert result["tenants_attempted"] == 0


@pytest.mark.asyncio
async def test_send_attention_supervisor_audit_digests_when_alerts_then_sends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        send_attention_supervisor_audit_digests,
    )

    tenant_id = uuid.uuid4()
    calls = {"send": 0, "invalidate": 0}

    async def _fake_build(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return {
            "digest_health_summary": {"never_sent": 1},
            "tenants": [
                {
                    "tenant_id": str(tenant_id),
                    "digest_health": "never_sent",
                },
            ],
        }

    async def _fake_send(*_args, **_kwargs):  # noqa: ANN002, ANN003
        calls["send"] += 1
        return {"sent": True, "tenant_id": str(tenant_id)}

    async def _fake_invalidate(**_kwargs) -> int:  # noqa: ANN003
        calls["invalidate"] += 1
        return 1

    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.build_supervisor_audit_digest_rollup",
        _fake_build,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest.send_supervisor_audit_digest_for_tenant",
        _fake_send,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.invalidate_supervisor_audit_rollup_cache",
        _fake_invalidate,
    )

    result = await send_attention_supervisor_audit_digests(object(), window_hours=168)  # type: ignore[arg-type]
    assert result["sent"] is True
    assert result["tenants_attempted"] == 1
    assert result["tenants_sent"] == 1
    assert calls["send"] == 1
    assert calls["invalidate"] == 1


def test_serialize_supervisor_audit_rollup_csv_has_header_row() -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import serialize_supervisor_audit_rollup_csv

    csv_text = serialize_supervisor_audit_rollup_csv({"tenants": []})
    assert csv_text.startswith("tenant_id,tenant_name")


@pytest.mark.asyncio
async def test_fetch_supervisor_audit_digest_rollup_uses_redis_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        fetch_supervisor_audit_digest_rollup,
    )
    from app.core.config import settings

    cached_payload = {
        "window_hours": 168,
        "generated_at": "2026-05-19T08:00:00+00:00",
        "tenants_active": 2,
        "tenants_total": 3,
        "total_actions": 5,
        "global_action_counts": {},
        "daily_trend": [],
        "tenants": [],
    }
    calls = {"build": 0}

    async def _fake_get_json(_key: str):  # noqa: ANN001
        return dict(cached_payload)

    async def _fake_set_json(_key: str, _value: object, *, ttl: int | None = None) -> None:  # noqa: ANN001
        del _key, _value, ttl

    async def _fake_build(*_args, **_kwargs):  # noqa: ANN002, ANN003
        calls["build"] += 1
        return dict(cached_payload)

    monkeypatch.setattr(settings, "supervisor_audit_rollup_cache_ttl_sec", 300)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.get_json",
        _fake_get_json,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.set_json",
        _fake_set_json,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.build_supervisor_audit_digest_rollup",
        _fake_build,
    )

    payload = await fetch_supervisor_audit_digest_rollup(object(), window_hours=168)  # type: ignore[arg-type]
    assert payload["cached"] is True
    assert calls["build"] == 0


def test_supervisor_audit_rollup_cache_windows_deduplicates_defaults() -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        supervisor_audit_rollup_cache_windows,
    )
    from app.core.config import settings

    settings.supervisor_audit_rollup_window_hours = 168
    assert supervisor_audit_rollup_cache_windows() == [24, 168]
    assert supervisor_audit_rollup_cache_windows(window_hours=48) == [48]


@pytest.mark.asyncio
async def test_invalidate_supervisor_audit_rollup_cache_deletes_known_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        invalidate_supervisor_audit_rollup_cache,
        supervisor_audit_rollup_cache_key,
    )
    from app.core.config import settings

    deleted: list[str] = []

    async def _fake_delete(key: str) -> int:
        deleted.append(key)
        return 1

    monkeypatch.setattr(settings, "supervisor_audit_rollup_cache_ttl_sec", 300)
    monkeypatch.setattr(settings, "supervisor_audit_rollup_window_hours", 168)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.redis_delete",
        _fake_delete,
    )

    removed = await invalidate_supervisor_audit_rollup_cache()
    assert removed == 2
    assert deleted == [
        supervisor_audit_rollup_cache_key(window_hours=24),
        supervisor_audit_rollup_cache_key(window_hours=168),
    ]


@pytest.mark.asyncio
async def test_invalidate_supervisor_audit_rollup_cache_noop_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        invalidate_supervisor_audit_rollup_cache,
    )
    from app.core.config import settings

    async def _fail_delete(_key: str) -> int:
        raise AssertionError("redis_delete should not run when cache TTL is disabled")

    monkeypatch.setattr(settings, "supervisor_audit_rollup_cache_ttl_sec", 0)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.redis_delete",
        _fail_delete,
    )

    assert await invalidate_supervisor_audit_rollup_cache() == 0


@pytest.mark.asyncio
async def test_fetch_supervisor_audit_digest_rollup_rebuilds_after_invalidation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.supervisor.session_audit_digest_rollup import (
        fetch_supervisor_audit_digest_rollup,
        invalidate_supervisor_audit_rollup_cache,
    )
    from app.core.config import settings

    cache: dict[str, dict[str, object]] = {}
    calls = {"build": 0}
    fresh_payload = {
        "window_hours": 168,
        "generated_at": "2026-05-19T09:00:00+00:00",
        "tenants_active": 1,
        "tenants_total": 1,
        "total_actions": 2,
        "global_action_counts": {},
        "daily_trend": [],
        "tenants": [],
    }

    async def _fake_get_json(key: str):  # noqa: ANN001
        return cache.get(key)

    async def _fake_set_json(key: str, value: object, *, ttl: int | None = None) -> None:  # noqa: ANN001
        del ttl
        cache[key] = dict(value)  # type: ignore[arg-type]

    async def _fake_delete(key: str) -> int:
        return 1 if cache.pop(key, None) is not None else 0

    async def _fake_build(*_args, **_kwargs):  # noqa: ANN002, ANN003
        calls["build"] += 1
        return dict(fresh_payload)

    monkeypatch.setattr(settings, "supervisor_audit_rollup_cache_ttl_sec", 300)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.get_json",
        _fake_get_json,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.set_json",
        _fake_set_json,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.redis_delete",
        _fake_delete,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.build_supervisor_audit_digest_rollup",
        _fake_build,
    )

    cache["supervisor:audit_rollup:v1:168"] = {
        "window_hours": 168,
        "generated_at": "2026-05-19T08:00:00+00:00",
        "tenants_active": 9,
        "tenants_total": 9,
        "total_actions": 99,
        "global_action_counts": {},
        "daily_trend": [],
        "tenants": [],
    }

    cached = await fetch_supervisor_audit_digest_rollup(object(), window_hours=168)  # type: ignore[arg-type]
    assert cached["cached"] is True
    assert cached["total_actions"] == 99
    assert calls["build"] == 0

    await invalidate_supervisor_audit_rollup_cache(window_hours=168)
    cache.clear()

    rebuilt = await fetch_supervisor_audit_digest_rollup(object(), window_hours=168)  # type: ignore[arg-type]
    assert rebuilt["cached"] is False
    assert rebuilt["total_actions"] == 2
    assert calls["build"] == 1
