"""Seven-step hive mission: Orchestrator → Managers → Workers → Managers → Orchestrator → Ballroom."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.executor import execute_universal_agent, hive_llm_credentials_ready
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.agent_config import AgentConfig
from app.models.enums import TaskType
from app.models.task import Task
from app.services.agent_universal import universal_execution_payload
from app.services.external_output_feed import record_orchestrator_delivery
from app.services.hive_ephemeral_sandbox import run_ephemeral_sandbox_probe
from app.services.hive_tier import FIXED_ORCHESTRATOR_AGENT_NAME, is_fixed_orchestrator_agent, resolve_hive_tier
from app.services.task_ledger import create_task_record

logger = get_logger(__name__)

MISSION_CORR_KEY = "hive_mission_correlation_id"
WORKER_LANE_KEY = "hive_mission_worker_lane"


def _strip_code_fences(raw: str) -> str:
    """Remove optional Markdown fences from model output."""

    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s, flags=re.IGNORECASE)
    return s.strip()


def _first_json_object(raw: str) -> dict[str, Any]:
    """Parse the first JSON object from a model response."""

    text = _strip_code_fences(raw)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        msg = "Model did not return a JSON object."
        raise ValueError(msg)
    return json.loads(text[start : end + 1])


def _fanout_transcript(session_id: uuid.UUID, agent: str, text: str) -> None:
    """Push a ballroom.transcript line (lazy import avoids router cycles)."""

    from app.api.routers import realtime_ballroom as rb

    clipped = text.strip()[:12_000]
    payload = rb._append_transcript(session_id, agent, clipped)
    if payload is not None:
        rb._broadcast_session_sync(session_id, payload)


def _fanout_orchestrator_delivery(
    *,
    session_id: uuid.UUID,
    orchestrator_label: str,
    text_report: str,
    voice_script: str,
) -> None:
    """Deliver final ballroom payload (text + voice script channel)."""

    from app.api.routers import realtime_ballroom as rb

    msg: dict[str, object] = {
        "type": "ballroom.orchestrator_out",
        "agent": orchestrator_label,
        "text": text_report.strip(),
        "voice_script": voice_script.strip(),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    cap = rb._ensure_capsule(session_id)
    hist = cap.setdefault("transcript", [])
    if isinstance(hist, list):
        hist.append(msg)
    rb._broadcast_session_sync(session_id, msg)


async def _load_agents_partitioned(session: AsyncSession) -> tuple[Agent | None, AgentConfig | None, list[Agent], list[Agent]]:
    """Fetch orchestrator plus manager/worker agent rows (tiers derived from persisted configs)."""

    stmt = (
        select(Agent)
        .options(selectinload(Agent.agent_config_row))
        .where(Agent.name == FIXED_ORCHESTRATOR_AGENT_NAME)
        .limit(1)
    )
    orch = await session.scalar(stmt)
    orch_cfg = None
    if orch is not None:
        orch_cfg = await session.scalar(select(AgentConfig).where(AgentConfig.agent_id == orch.id))

    stmt_all = select(Agent, AgentConfig).outerjoin(AgentConfig, AgentConfig.agent_id == Agent.id)
    rows = (await session.execute(stmt_all)).all()
    managers: list[Agent] = []
    workers: list[Agent] = []
    for row_agent, cfg in rows:
        if is_fixed_orchestrator_agent(row_agent):
            continue
        tier = resolve_hive_tier(agent=row_agent, agent_config=cfg)
        if tier == "manager":
            managers.append(row_agent)
        elif tier == "worker":
            workers.append(row_agent)
    return orch, orch_cfg, managers, workers


async def _llm_router_text(
    session: AsyncSession,
    *,
    system_prompt: str,
    user_payload: str,
    swarm_id: str,
    task_slug: str,
) -> tuple[str, float | None]:
    """Thin wrapper around LiteLLMRouter."""

    router = LiteLLMRouter()
    return await router.decompose(
        session,
        system_prompt=system_prompt,
        user_payload=user_payload,
        swarm_id=swarm_id,
        task_id=task_slug,
    )


async def _run_delegate_worker(
    session: AsyncSession,
    *,
    worker: Agent,
    cfg: AgentConfig | None,
    instruction: str,
    user_brief: str,
    mission_id: uuid.UUID,
    manager_name: str,
) -> tuple[str, dict[str, Any]]:
    """Execute one worker bee via universal executor inside the mission."""

    payload = dict(universal_execution_payload(worker, cfg))
    payload[MISSION_CORR_KEY] = str(mission_id)
    payload[WORKER_LANE_KEY] = True
    payload["user_prompt_template"] = (
        f"{instruction.strip()}\n\n## Hive mission brief (context)\n{user_brief.strip()[:6000]}"
    )

    task_row = await create_task_record(
        session,
        title=f"Hive mission · {manager_name} · {worker.name}",
        task_type_value=TaskType.AGENT_RUN,
        priority=5,
        payload=dict(payload),
        swarm_id=None,
        workflow_id=None,
        parent_task_id=None,
    )
    await session.flush()
    task_row.agent_id = worker.id
    await session.flush()

    snapshot = await execute_universal_agent(
        session,
        agent_config=dict(payload),
        task_id=task_row.id,
    )
    row = await session.get(Task, task_row.id)
    out_txt = ""
    if row and isinstance(row.result, dict):
        out_txt = str(row.result.get("output", "") or "")
    elif row:
        out_txt = str(row.result or "")
    return out_txt.strip(), snapshot


async def run_seven_step_mission(
    session: AsyncSession,
    *,
    user_brief: str,
    session_id: uuid.UUID,
    hive_subject: str,
) -> dict[str, Any]:
    """Drive the mandated Orchestrator→Manager→Worker→Manager→Orchestrator Ballroom chain."""

    mission_id = uuid.uuid4()
    brief = user_brief.strip()
    if len(brief) < 3:
        msg = "user_brief too short"
        raise ValueError(msg)

    orch, orch_cfg, managers, workers = await _load_agents_partitioned(session)
    if orch is None or orch_cfg is None:
        msg = "Fixed Orchestrator row or config missing — run Alembic seed migration."
        raise RuntimeError(msg)

    manager_cfgs = {
        row.id: (await session.scalar(select(AgentConfig).where(AgentConfig.agent_id == row.id))) for row in managers
    }
    worker_cfgs = {
        row.id: (await session.scalar(select(AgentConfig).where(AgentConfig.agent_id == row.id))) for row in workers
    }

    worker_catalog = "\n".join(f"- {w.id} · {w.name}" for w in workers) or "(none — seed worker bees)"
    manager_catalog = "\n".join(f"- {m.id} · {m.name}" for m in managers) or "(none — seed managers)"

    _fanout_transcript(session_id, orch.name, "Rozkladám úlohu a vyberám manažérov.")

    orch_system = orch_cfg.system_prompt
    mgr_pick_raw, _mgr_cost = await _llm_router_text(
        session,
        system_prompt=orch_system,
        user_payload=(
            "You ONLY assign hive MANAGERS.\n\n"
            f"USER BRIEF:\n{brief}\n\n"
            "MANAGERS (pick zero or more UUIDs):\n"
            f"{manager_catalog}\n\n"
            'Reply with ONLY JSON: {"manager_ids":["uuid",...],"rationale":"..."} '
            "(empty manager_ids allowed if managers list is empty)."
        ),
        swarm_id=str(session_id),
        task_slug=f"orch_mgr_pick-{mission_id}",
    )

    mgr_plan: dict[str, Any] = {}
    selected_manager_ids: list[uuid.UUID] = []
    try:
        mgr_plan = _first_json_object(mgr_pick_raw)
        raw_ids = mgr_plan.get("manager_ids") or []
        selected_manager_ids = [uuid.UUID(str(x)) for x in raw_ids][:8]
    except (ValueError, TypeError, KeyError) as exc:
        logger.warning("hive_mission.manager_parse_fallback", error=str(exc))
        selected_manager_ids = [m.id for m in managers[: min(3, len(managers))]]

    selected_managers = [m for m in managers if m.id in selected_manager_ids]
    if not selected_managers and managers:
        selected_managers = managers[: min(3, len(managers))]

    rationale = str(mgr_plan.get("rationale") or "")

    _fanout_transcript(
        session_id,
        orch.name,
        f"Manažéri: {', '.join(m.name for m in selected_managers) or '(žiadni)'} — {rationale[:400]}",
    )

    manager_deliverables: list[str] = []
    sandbox_requested = any(
        k in brief.lower() for k in ("sandbox", "simulation", "simul", "docker", "verif", "verified container")
    )
    sandbox_probes: list[dict[str, Any]] = []

    for mgr in selected_managers:
        mcfg = manager_cfgs.get(mgr.id)
        m_prompt = str(mcfg.system_prompt if mcfg is not None else "You coordinate worker bees.")

        del_raw, _del_cost = await _llm_router_text(
            session,
            system_prompt=m_prompt,
            user_payload=(
                "You MUST delegate ONLY to WORKER bees listed below.\n"
                'Return ONLY JSON {"delegations":[{"worker_id":"uuid","instruction":"text"}],'
                '"plan":"why"}. Max 8 delegations.\n\n'
                f"USER BRIEF:\n{brief}\n\n"
                "WORKERS:\n"
                f"{worker_catalog}\n"
            ),
            swarm_id=str(session_id),
            task_slug=f"mgr_delegate-{mgr.id}-{mission_id}",
        )

        try:
            dels = _first_json_object(del_raw)
            delegation_list = dels.get("delegations") or []
        except (ValueError, TypeError):
            delegation_list = []

        worker_outputs: list[str] = []
        for item in delegation_list[:8]:
            if not isinstance(item, dict):
                continue
            try:
                wid = uuid.UUID(str(item.get("worker_id")))
                instruction_text = str(item.get("instruction") or "Gather relevant data.")
            except (ValueError, TypeError):
                continue
            wrow = next((w for w in workers if w.id == wid), None)
            if wrow is None:
                continue

            _fanout_transcript(session_id, mgr.name, f"Robotník {wrow.name}: {instruction_text[:300]}…")
            out_text, _snap = await _run_delegate_worker(
                session,
                worker=wrow,
                cfg=worker_cfgs.get(wid),
                instruction=instruction_text,
                user_brief=brief,
                mission_id=mission_id,
                manager_name=mgr.name,
            )
            worker_outputs.append(f"### {wrow.name}\n{out_text[:8000]}")

        combined_workers = "\n\n".join(worker_outputs) or "(Žiadny výstup z robotníkov.)"

        sandbox_note = ""
        if sandbox_requested:
            probe = await run_ephemeral_sandbox_probe(
                swarm_id=mgr.id,
                workflow_id=orch.id,
                task_id=mission_id,
            )
            if probe:
                sandbox_note = f"Sandbox stdout ({probe.duration_sec:.2f}s): {probe.stdout[:1600]}".strip()
                sandbox_probes.append(
                    {
                        "manager_id": str(mgr.id),
                        "manager_name": mgr.name,
                        "duration_sec": probe.duration_sec,
                        "stdout": probe.stdout[:4000],
                        "stderr": probe.stderr[:1000],
                        "container_id": probe.container_id,
                    },
                )
                _fanout_transcript(session_id, mgr.name, f"Sandbox probe dokončený ({probe.duration_sec:.1f}s).")
            else:
                sandbox_note = "Sandbox probe unavailable (Docker/disable)."
                sandbox_probes.append(
                    {
                        "manager_id": str(mgr.id),
                        "manager_name": mgr.name,
                        "ok": False,
                        "note": "probe_unavailable",
                    },
                )
                _fanout_transcript(session_id, mgr.name, sandbox_note)

        merge_raw, _merge_cost = await _llm_router_text(
            session,
            system_prompt=m_prompt,
            user_payload=(
                "Synthesize grounded manager notes from worker payloads. "
                "Output concise Markdown bullet summary plus a Closing paragraph.\n\n"
                "## Worker payloads\n"
                f"{combined_workers}\n\n"
                "## Sandbox\n"
                f"{sandbox_note or '(none)'}\n\n"
                "## Brief reminder\n"
                f"{brief[:2000]}\n"
            ),
            swarm_id=str(session_id),
            task_slug=f"mgr_merge-{mgr.id}-{mission_id}",
        )
        manager_deliverables.append(f"## Manažér {mgr.name}\n{merge_raw.strip()}")
        _fanout_transcript(session_id, mgr.name, "Spracované — výsledok posielam orchestrátorovi.")

    stitched = "\n\n".join(manager_deliverables) or "(Žiadni manažéri nevytvorili obsah.)"

    simulation_outcome: dict[str, Any] | None
    if sandbox_requested:
        simulation_outcome = {"probes": sandbox_probes}
    else:
        simulation_outcome = None

    _fanout_transcript(session_id, orch.name, "Zostavujem finálny report a hlasové zhrnutie.")

    voice_script = stitched[:2400]
    final_markdown = stitched.strip()

    if hive_llm_credentials_ready():
        v_raw, _v_cost = await _llm_router_text(
            session,
            system_prompt=orch_system,
            user_payload=(
                "Produce TWO sections exactly:\nSECTION_TEXT: (Markdown report)\n"
                "SECTION_VOICE: (Spoken narration under ~120 words, plain text, for speech synthesis — "
                "no bullets, conversational, concise.)\n\n"
                "## Manager bundle\n"
                f"{stitched[:12_000]}\n\n## Original brief\n{brief[:4000]}\n"
            ),
            swarm_id=str(session_id),
            task_slug=f"orch_final-{mission_id}",
        )
        upper = v_raw
        if "SECTION_TEXT:" in upper and "SECTION_VOICE:" in upper:
            txt_part = upper.split("SECTION_TEXT:", 1)[1].split("SECTION_VOICE:", 1)[0].strip()
            spk_part = upper.split("SECTION_VOICE:", 1)[1].strip()
            if txt_part:
                final_markdown = txt_part
            if spk_part:
                voice_script = spk_part

    _fanout_orchestrator_delivery(
        session_id=session_id,
        orchestrator_label=orch.name,
        text_report=final_markdown,
        voice_script=voice_script,
    )

    dash_uid = parse_dashboard_user_subject(hive_subject)
    payload_meta: dict[str, Any] = {
        "mission_id": str(mission_id),
        "session_id": str(session_id),
        "orchestrator_id": str(orch.id),
        "managers_used": [str(m.id) for m in selected_managers],
        "status": "delivered_via_orchestrator",
        "user_brief_excerpt": brief[:500],
    }
    if dash_uid is not None:
        await record_orchestrator_delivery(
            session,
            dashboard_user_id=dash_uid,
            mission_id=mission_id,
            session_id=session_id,
            text_report=final_markdown,
            voice_script=voice_script,
            output_metadata=payload_meta,
            simulation_outcome=simulation_outcome,
            tags=[],
            orchestrator_agent_id=orch.id,
        )
    else:
        logger.info(
            "hive_mission.external_feed_skipped",
            agent_id=str(orch.id),
            swarm_id=str(session_id),
            task_id=str(mission_id),
            reason="non_dashboard_subject",
        )

    return {
        "mission_id": str(mission_id),
        "session_id": str(session_id),
        "orchestrator": str(orch.id),
        "managers_used": [str(m.id) for m in selected_managers],
        "status": "delivered_via_orchestrator",
        "hive_subject": hive_subject,
    }
