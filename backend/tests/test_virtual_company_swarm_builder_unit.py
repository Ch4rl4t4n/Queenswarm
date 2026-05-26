"""Unit tests for Virtual Company server-side swarm wizard."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.virtual_company_swarm_builder import (
    SWARM_WIZARD_SPECS,
    build_department_swarm,
    find_swarm_by_wizard_template,
)


@pytest.mark.asyncio
async def test_build_department_swarm_idempotent_when_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import virtual_company_swarm_builder as mod

    existing = MagicMock()
    existing.id = uuid.uuid4()

    async def _find(*_a: object, **_k: object) -> MagicMock:
        return existing

    monkeypatch.setattr(mod, "find_swarm_by_wizard_template", _find)

    tenant = MagicMock()
    tenant.operator_settings = {}
    result = await mod.build_department_swarm(
        AsyncMock(),
        tenant=tenant,
        template_id="marketing-ops",
    )
    assert result["status"] == "already_exists"
    assert result["swarm_id"] == str(existing.id)


@pytest.mark.asyncio
async def test_build_department_swarm_unknown_template() -> None:
    tenant = MagicMock()
    tenant.operator_settings = {}
    with pytest.raises(KeyError):
        await build_department_swarm(
            AsyncMock(),
            tenant=tenant,
            template_id="unknown-template",
        )


def test_swarm_wizard_specs_cover_six_departments() -> None:
    dept_ids = {
        spec.department_id
        for spec in SWARM_WIZARD_SPECS.values()
        if spec.category == "virtual_company"
    }
    assert dept_ids == {"marketing", "sales", "finance", "digital", "rnd", "product"}


def test_life_os_wizard_spec_present() -> None:
    spec = SWARM_WIZARD_SPECS.get("life-os")
    assert spec is not None
    assert spec.category == "personal"
    assert spec.routine is not None
    assert spec.routine.cron_expr == "0 6 * * *"
    assert len(spec.agents) == 4


@pytest.mark.asyncio
async def test_find_swarm_by_wizard_template_empty() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    found = await find_swarm_by_wizard_template(session, template_id="marketing-ops")
    assert found is None
