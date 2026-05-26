"""Unit tests for solo operator lane bootstrap."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.solo_operator_bootstrap import ensure_solo_operator_lane_bootstrap
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine


@pytest.mark.asyncio
async def test_ensure_solo_operator_lane_bootstrap_when_no_routines_creates_lanes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    maintainer = SupervisorRoutine(
        name="Queen Maintainer",
        goal_template="maintain",
        tenant_id=tenant_id,
        schedule_kind="interval",
        interval_seconds=3600,
        runtime_mode="durable",
        roles=["coder"],
        is_active=True,
    )
    maintainer.id = uuid.uuid4()

    async def _fake_maintainer(*_args, **_kwargs):
        return maintainer

    created: list[str] = []

    async def _fake_create(_db, **kwargs):
        row = SupervisorRoutine(
            name=kwargs["name"],
            goal_template=kwargs["goal_template"],
            tenant_id=tenant_id,
            schedule_kind=kwargs["schedule_kind"],
            runtime_mode=kwargs["runtime_mode"],
            roles=kwargs["roles"],
            is_active=True,
        )
        row.id = uuid.uuid4()
        created.append(kwargs["name"])
        return row

    async def _fake_sentinel(*_args, **_kwargs):
        return {"status": "exists", "routine_id": str(uuid.uuid4())}

    monkeypatch.setattr(
        "app.application.services.solo_operator_bootstrap.ensure_queen_maintainer_routine",
        _fake_maintainer,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_bootstrap.ensure_sentinel_upgrade_routine",
        _fake_sentinel,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_bootstrap.create_supervisor_routine",
        _fake_create,
    )

    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.scalar = AsyncMock(return_value=None)
    db.flush = AsyncMock()

    payload = await ensure_solo_operator_lane_bootstrap(
        db,
        tenant_id=tenant_id,
        created_by_subject="test@example.com",
    )

    assert payload["lanes_bound"] >= 2
    assert payload["bank_po_weekly"]["status"] in {"created", "exists"}
    assert "Life OS morning briefing" in created or payload["trio_lanes"]
