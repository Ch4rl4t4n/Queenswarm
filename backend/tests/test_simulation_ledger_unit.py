"""Unit tests for swarm simulation audit persistence."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.outcome_verification import max_simulator_confidence_fraction


def test_max_simulator_confidence_fraction_picks_peak() -> None:
    rows = [
        {
            "status": "completed",
            "agent_role": "simulator",
            "result": {"confidence": 0.55},
        },
        {
            "status": "completed",
            "agent_role": "simulator",
            "result": {"confidence": 0.91},
        },
    ]
    peak = max_simulator_confidence_fraction(rows)
    assert peak is not None
    assert abs(peak - 0.91) < 1e-6


@pytest.mark.asyncio
async def test_record_swarm_simulation_row_skipped_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.simulation_ledger.settings.simulation_audit_rows_enabled", False)

    from app.services.simulation_ledger import record_swarm_simulation_row

    session = AsyncMock()
    sid = uuid.uuid4()
    wid = uuid.uuid4()
    row = await record_swarm_simulation_row(
        session,
        task_id=None,
        swarm_id=sid,
        workflow_id=wid,
        internal_step_outputs=[],
        graph_error=None,
        verification_passed=False,
        verification_notes=[],
    )
    assert row is None
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_record_swarm_simulation_row_pass_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.simulation_ledger.settings.simulation_audit_rows_enabled", True)
    monkeypatch.setattr("app.services.simulation_ledger.settings.reward_threshold_pass", 0.7)
    monkeypatch.setattr("app.services.simulation_ledger.settings.simulation_docker_execution_enabled", False)

    from app.models.enums import SimulationResult
    from app.services.simulation_ledger import record_swarm_simulation_row

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    sid = uuid.uuid4()
    wid = uuid.uuid4()
    tid = uuid.uuid4()
    internals = [
        {
            "status": "completed",
            "agent_role": "simulator",
            "result": {"verification_passed": True, "confidence": 0.95},
        },
    ]

    entity = await record_swarm_simulation_row(
        session,
        task_id=tid,
        swarm_id=sid,
        workflow_id=wid,
        internal_step_outputs=internals,
        graph_error=None,
        verification_passed=True,
        verification_notes=["verification_ok"],
    )
    assert entity is not None
    assert entity.result_type == SimulationResult.PASS
    assert entity.confidence_pct >= 70.0
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_record_swarm_simulation_row_attachs_probe_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.simulation_ledger.settings.simulation_audit_rows_enabled", True)
    monkeypatch.setattr("app.services.simulation_ledger.settings.reward_threshold_pass", 0.7)
    monkeypatch.setattr(
        "app.services.simulation_ledger.settings.simulation_docker_execution_enabled",
        True,
    )

    from app.services.hive_ephemeral_sandbox import SandboxProbeResult
    from app.services.simulation_ledger import record_swarm_simulation_row

    probe = SandboxProbeResult(
        container_id="beefcafeabcd",
        stdout="probe-ok\n",
        stderr="",
        duration_sec=0.042,
    )

    async def fake_probe(**kwargs):  # noqa: ANN003,ARG001
        del kwargs
        return probe

    monkeypatch.setattr("app.services.simulation_ledger.run_ephemeral_sandbox_probe", fake_probe)

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    sid = uuid.uuid4()
    wid = uuid.uuid4()

    entity = await record_swarm_simulation_row(
        session,
        task_id=None,
        swarm_id=sid,
        workflow_id=wid,
        internal_step_outputs=[],
        graph_error=None,
        verification_passed=False,
        verification_notes=[],
    )
    assert entity is not None
    assert entity.docker_container_id == probe.container_id
    assert entity.stdout == probe.stdout
    assert entity.duration_sec == pytest.approx(probe.duration_sec, rel=1e-9)
    assert entity.scenario["synthetic_audit"] is False


@pytest.mark.asyncio
async def test_record_swarm_simulation_row_synthetic_when_probe_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.simulation_ledger.settings.simulation_audit_rows_enabled", True)
    monkeypatch.setattr(
        "app.services.simulation_ledger.settings.simulation_docker_execution_enabled",
        True,
    )

    async def fake_probe_failed(**kwargs):  # noqa: ANN003,ARG001
        del kwargs
        return None

    monkeypatch.setattr(
        "app.services.simulation_ledger.run_ephemeral_sandbox_probe",
        fake_probe_failed,
    )

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    from app.services.simulation_ledger import record_swarm_simulation_row

    entity = await record_swarm_simulation_row(
        session,
        task_id=None,
        swarm_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        internal_step_outputs=[],
        graph_error=None,
        verification_passed=False,
        verification_notes=[],
    )
    assert entity is not None
    assert entity.docker_container_id is None
    assert entity.scenario["synthetic_audit"] is True
    assert entity.scenario["docker_probe_succeeded"] is False
