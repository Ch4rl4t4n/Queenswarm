"""Seven-step hive mission: Orchestrator → dynamic managers → workers → Ballroom."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.agents.executor import execute_universal_agent, hive_llm_credentials_ready
from app.domain.agents.managers.registry import get_manager_template
from app.infrastructure.connectors.dynamic.service import describe_connector_catalog_addon, merged_static_and_dynamic_allowlist
from app.core.config import get_settings
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.enums import TaskStatus, TaskType
from app.infrastructure.persistence.models.task import Task
from app.domain.recipes.library import semantic_search_catalog
from app.common.schemas.workflow_breaker import PreviewDecompositionResponse
from app.application.services.agent_universal import universal_execution_payload
from app.application.services.external_output_feed import record_orchestrator_delivery
from app.application.services.hive_ephemeral_sandbox import run_ephemeral_sandbox_probe
from app.application.services.hive_tier import FIXED_ORCHESTRATOR_AGENT_NAME, is_fixed_orchestrator_agent, resolve_hive_tier
from app.application.services.swarm_manager_selection import (
    cap_template_list,
    describe_template_catalog_compact,
    ensure_execution_lane,
    heuristic_manager_slugs,
    parse_orchestrator_template_pick,
)
from app.domain.hive_mind.ingest import HiveMindExtras
from app.domain.hive_mind.service import HiveMindService
from app.domain.outputs.engine import OutputEngine, build_fallback_structured
from app.domain.outputs.parsing import coalesce_json_text, split_orchestrator_deliverable_sections
from app.domain.outputs.service import slugify_fragment
from app.application.services.swarm_post_mortem import run_ballroom_post_mortem_persistence
from app.application.services.task_ledger import create_task_record
from app.application.services.workflow_breaker.breaker import WorkflowBreakerService

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


def _breaker_digest_preview(preview: PreviewDecompositionResponse | None) -> str:
    """Serialize breaker preview rows for orch + post-mortem metadata."""

    if preview is None:
        return "(Workflow Breaker preview unavailable)"
    ordered = sorted(preview.steps, key=lambda row: row.step_order)
    lines = [f"{row.step_order}. {row.agent_role.value}: {row.description.strip()[:240]}" for row in ordered]
    rationale = preview.decomposition_rationale.strip()
    excerpt = rationale[:1400]
    return (
        "## Breaker steps\n"
        + "\n".join(lines)
        + f"\n\n## Rationale excerpt\n{excerpt}\n\n## Parallel hints\n{preview.parallel_groups}"
    )


async def _lane_recipe_hints(
    session: AsyncSession,
    *,
    brief: str,
    lane_slug: str,
    mission_id: uuid.UUID,
) -> str:
    """Pull compact Recipe Library rows for imitation-friendly overlays."""

    try:
        hits = await semantic_search_catalog(
            session,
            query=f"{brief.strip()[:2000]} :: {lane_slug}",
            limit=2,
            task_id=str(mission_id),
        )
    except SQLAlchemyError as exc:
        logger.warning(
            "hive_mission.semantic_hints_failed",
            swarm_id=str(mission_id),
            task_id=str(mission_id),
            error=str(exc),
        )
        return "(recipe search skipped — persistence error)"

    bullets: list[str] = []
    for hit in hits:
        label = hit.postgres_row.name if hit.postgres_row is not None else hit.chroma_document_id
        bullets.append(f"- {label} (sim≈{hit.similarity:.3f})")
    return "\n".join(bullets) if bullets else "(žiadne knižné trafy)"


def _lane_system_prompt(slug: str, *, hints: str, connector_allowlist: tuple[str, ...]) -> str:
    """Fuse Markdown persona instructions with Recipe Library excerpts."""

    spec = get_manager_template(slug)
    allow = ", ".join(connector_allowlist) or "(text-only connectors)"
    roles = ", ".join(role.value for role in spec.sub_swarm_roles)
    return (
        f"{spec.prompt_text()}\n\n"
        "### Connector policy\n"
        f"Dovolené konektory: **{allow}**. Odmietni neschválené MCP sloty.\n\n"
        "### Sub-swarm (2–5 bees)\n"
        f"Mentálne mapuj roly **{roles}** — paralelne max 5 a vždy drž budget.\n\n"
        "### Knižné nápovedy\n"
        f"{hints}\n"
    )


async def _fanout_transcript(session_id: uuid.UUID, agent: str, text: str) -> None:
    """Push a ballroom.transcript line (lazy import avoids router cycles)."""

    from app.presentation.api.routers import realtime_ballroom as rb

    clipped = text.strip()[:12_000]
    await rb.append_ballroom_transcript_line_public(session_id, agent, clipped, broadcast=True)


async def _fanout_orchestrator_delivery(
    *,
    session_id: uuid.UUID,
    orchestrator_label: str,
    text_report: str,
    voice_script: str,
) -> None:
    """Deliver final ballroom payload (text + voice script channel)."""

    from app.presentation.api.routers import realtime_ballroom as rb

    msg: dict[str, object] = {
        "type": "ballroom.orchestrator_out",
        "agent": orchestrator_label,
        "text": text_report.strip(),
        "voice_script": voice_script.strip(),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    await rb.append_ballroom_orchestrator_out_public(session_id, msg)


async def _load_agents_partitioned(session: AsyncSession) -> tuple[Agent | None, AgentConfig | None, list[Agent], list[Agent]]:
    """Fetch orchestrator plus persisted manager/worker rows (workers still required)."""

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
    manager_template_slug: str,
    connector_allowlist: tuple[str, ...],
) -> tuple[str, dict[str, Any]]:
    """Execute one worker bee via universal executor inside the mission."""

    payload = dict(universal_execution_payload(worker, cfg))
    payload[MISSION_CORR_KEY] = str(mission_id)
    payload[WORKER_LANE_KEY] = True
    payload["manager_template_slug"] = manager_template_slug
    payload["manager_connector_allowlist"] = list(connector_allowlist)
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
    """Drive Orchestrator-led missions with seeded manager templates + worker fan-out."""

    mission_id = uuid.uuid4()
    brief = user_brief.strip()
    if len(brief) < 3:
        msg = "user_brief too short"
        raise ValueError(msg)

    orch, orch_cfg, _persisted_manager_rows, workers = await _load_agents_partitioned(session)
    if orch is None or orch_cfg is None:
        msg = "Fixed Orchestrator row or config missing — run Alembic seed migration."
        raise RuntimeError(msg)

    session.add(
        Task(
            id=mission_id,
            title=f"Ballroom mission · {brief[:160]}",
            task_type=TaskType.AGENT_RUN,
            status=TaskStatus.RUNNING,
            priority=5,
            payload={
                "kind": "ballroom_seven_step_mission",
                "session_id": str(session_id),
                "brief_excerpt": brief[:1500],
            },
            agent_id=orch.id,
            swarm_id=None,
            workflow_id=None,
            parent_task_id=None,
            started_at=datetime.now(tz=UTC),
        ),
    )
    await session.flush()

    worker_cfgs = {
        row.id: (await session.scalar(select(AgentConfig).where(AgentConfig.agent_id == row.id))) for row in workers
    }

    worker_catalog = "\n".join(f"- {w.id} · {w.name}" for w in workers) or "(none — seed worker bees)"
    settings = get_settings()
    orch_hive = ""
    if settings.hive_mind_enabled:
        orch_hive = await HiveMindService.query_for_prompt(
            relevance_to_current_task=brief,
            settings=settings,
            swarm_id=str(session_id),
            task_id=str(mission_id),
            agent_id=str(orch.id),
        )
        if orch_hive:
            logger.info(
                "hive_mission.hive_mind_orchestrator_recall_ready",
                agent_id=str(orch.id),
                swarm_id=str(session_id),
                task_id=str(mission_id),
            )
    orch_hive_prefix = f"{orch_hive}\n\n" if orch_hive else ""
    heuristic_seed = heuristic_manager_slugs(None, specialist_worker_count=len(workers), settings=settings)

    preview: PreviewDecompositionResponse | None = None
    await _fanout_transcript(session_id, orch.name, "Workflow Breaker: živý náhľad rozkladu.")

    try:
        preview = await WorkflowBreakerService().preview_workflow_plan(
            session,
            task_text=brief,
            matching_recipe_id=None,
            enrich_from_chroma_recipes=True,
            max_steps=7,
            swarm_id=str(session_id),
            agent_task_id=str(mission_id),
        )
    except (ValidationError, ValueError, RuntimeError, SQLAlchemyError, TypeError) as exc:
        logger.warning(
            "hive_mission.breaker_preview_failed",
            agent_id=str(orch.id),
            swarm_id=str(session_id),
            task_id=str(mission_id),
            error=str(exc),
        )

    if preview is not None:
        heuristic_seed = heuristic_manager_slugs(preview, specialist_worker_count=len(workers), settings=settings)
    breaker_digest_text = _breaker_digest_preview(preview)

    orch_system = orch_cfg.system_prompt
    template_catalog_md = describe_template_catalog_compact()
    catalog_addon = await describe_connector_catalog_addon(session)
    if catalog_addon.strip():
        template_catalog_md = f"{template_catalog_md}\n\n{catalog_addon}"

    await _fanout_transcript(session_id, orch.name, "Orchestrator: výber dynamických manažérskych šablón.")

    mgr_pick_raw, _mgr_cost = await _llm_router_text(
        session,
        system_prompt=orch_system,
        user_payload=(
            f"{orch_hive_prefix}"
            "You orchestrate PHASE 0.5 Ballroom missions.\n"
            "Pick **manager template slugs** ( Recipe-seeded personas ), not legacy DB UUID managers.\n\n"
            f"USER BRIEF:\n{brief}\n\n"
            "### Template catalog\n"
            f"{template_catalog_md}\n\n"
            "### Workflow Breaker digest\n"
            f"{breaker_digest_text}\n\n"
            "### Heuristic seed (fallback)\n"
            f"{json.dumps(heuristic_seed)}\n\n"
            "### Workers reachable\n"
            f"count={len(workers)}\n{worker_catalog}\n\n"
            'Respond ONLY JSON: {"template_slugs":["research_intelligence",...],"rationale":"why"} '
            "(subset allowed; omit unknown slugs)."
        ),
        swarm_id=str(session_id),
        task_slug=f"orch_mt_pick-{mission_id}",
    )

    try:
        plan_obj = _first_json_object(mgr_pick_raw)
        candidate_slugs = parse_orchestrator_template_pick(plan_obj, heuristic_seed)
        rationale_text = str(plan_obj.get("rationale") or "")
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        logger.warning(
            "hive_mission.manager_template_parse_fallback",
            agent_id=str(orch.id),
            swarm_id=str(session_id),
            task_id=str(mission_id),
            error=str(exc),
        )
        candidate_slugs = list(heuristic_seed)
        rationale_text = "fallback_heuristic_templates"

    selected_slugs = cap_template_list(
        ensure_execution_lane(candidate_slugs, specialists_available=bool(workers)),
        settings=settings,
    )
    if not selected_slugs:
        selected_slugs = cap_template_list(
            ensure_execution_lane(list(heuristic_seed), specialists_available=bool(workers)),
            settings=settings,
        )

    lane_labels = [get_manager_template(slug).display_name for slug in selected_slugs]
    await _fanout_transcript(
        session_id,
        orch.name,
        f"Šablóny manažérov ({len(selected_slugs)}): {', '.join(lane_labels) or '(žiadne)'} — "
        f"{rationale_text[:360]}",
    )

    manager_deliverables: list[str] = []
    sandbox_requested = any(
        k in brief.lower() for k in ("sandbox", "simulation", "simul", "docker", "verif", "verified container")
    )
    sandbox_probes: list[dict[str, Any]] = []
    max_workers_per_lane = int(settings.swarm_max_concurrent_specialist_workers)

    for lane_slug in selected_slugs:
        spec = get_manager_template(lane_slug)
        merged_allow = await merged_static_and_dynamic_allowlist(session, manager_template_slug=lane_slug)
        hints = await _lane_recipe_hints(session, brief=brief, lane_slug=lane_slug, mission_id=mission_id)
        m_prompt = _lane_system_prompt(lane_slug, hints=hints, connector_allowlist=merged_allow)
        lane_title = spec.display_name
        lane_hive_prefix = ""
        if settings.hive_mind_enabled:
            lane_block = await HiveMindService.query_for_prompt(
                relevance_to_current_task=f"{brief[:3600]}\n### Manager lane\nTemplate slug: `{lane_slug}` ({lane_title})\n{m_prompt[:1200]}",
                settings=settings,
                swarm_id=str(session_id),
                task_id=str(mission_id),
                agent_id=str(orch.id),
            )
            lane_hive_prefix = f"{lane_block}\n\n" if lane_block else ""

        del_raw, _del_cost = await _llm_router_text(
            session,
            system_prompt=m_prompt,
            user_payload=(
                f"{lane_hive_prefix}"
                "You coordinate specialist WORKER bees from the hive roster listed below.\n"
                'Return ONLY JSON {"delegations":[{"worker_id":"uuid","instruction":"text"}],'
                '"plan":"why"}.\n\n'
                f"HOST TEMPLATE SLUG: {lane_slug}\n"
                f"CONNECTOR ALLOWLIST: {list(merged_allow)}\n"
                f"MAX DELEGATIONS: {max_workers_per_lane}\n\n"
                f"USER BRIEF:\n{brief}\n\n"
                "WORKERS:\n"
                f"{worker_catalog}\n"
            ),
            swarm_id=str(session_id),
            task_slug=f"mgr_delegate-{lane_slug}-{mission_id}",
        )

        try:
            dels = _first_json_object(del_raw)
            delegation_list = dels.get("delegations") or []
        except (ValueError, TypeError, json.JSONDecodeError):
            delegation_list = []

        worker_outputs: list[str] = []
        for item in delegation_list[:max_workers_per_lane]:
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

            await _fanout_transcript(session_id, lane_title, f"Robotník {wrow.name}: {instruction_text[:300]}…")
            out_text, _snap = await _run_delegate_worker(
                session,
                worker=wrow,
                cfg=worker_cfgs.get(wid),
                instruction=instruction_text,
                user_brief=brief,
                mission_id=mission_id,
                manager_name=lane_title,
                manager_template_slug=lane_slug,
                connector_allowlist=merged_allow,
            )
            worker_outputs.append(f"### {wrow.name}\n{out_text[:8000]}")

        combined_workers = "\n\n".join(worker_outputs) or "(Žiadny výstup z robotníkov.)"

        sandbox_note = ""
        if sandbox_requested and lane_slug == "execution_operations":
            probe = await run_ephemeral_sandbox_probe(
                swarm_id=orch.id,
                workflow_id=orch.id,
                task_id=mission_id,
            )
            if probe:
                sandbox_note = f"Sandbox stdout ({probe.duration_sec:.2f}s): {probe.stdout[:1600]}".strip()
                sandbox_probes.append(
                    {
                        "lane_slug": lane_slug,
                        "lane_title": lane_title,
                        "duration_sec": probe.duration_sec,
                        "stdout": probe.stdout[:4000],
                        "stderr": probe.stderr[:1000],
                        "container_id": probe.container_id,
                    },
                )
                await _fanout_transcript(session_id, lane_title, f"Sandbox probe dokončený ({probe.duration_sec:.1f}s).")
            else:
                sandbox_note = "Sandbox probe unavailable (Docker/disable)."
                sandbox_probes.append(
                    {
                        "lane_slug": lane_slug,
                        "lane_title": lane_title,
                        "ok": False,
                        "note": "probe_unavailable",
                    },
                )
                await _fanout_transcript(session_id, lane_title, sandbox_note)

        merge_raw, _merge_cost = await _llm_router_text(
            session,
            system_prompt=m_prompt,
            user_payload=(
                f"{lane_hive_prefix}"
                "Synthesize grounded manager notes from worker payloads — Markdown bullets + Closing.\n\n"
                "## Worker payloads\n"
                f"{combined_workers}\n\n"
                "## Sandbox\n"
                f"{sandbox_note or '(none)'}\n\n"
                "## Brief reminder\n"
                f"{brief[:2000]}\n"
            ),
            swarm_id=str(session_id),
            task_slug=f"mgr_merge-{lane_slug}-{mission_id}",
        )
        manager_deliverables.append(f"## {lane_title}\n{merge_raw.strip()}")
        await _fanout_transcript(session_id, lane_title, "Spracované — výsledok posielam orchestrátorovi.")

    stitched = "\n\n".join(manager_deliverables) or "(Žiadni manažéri nevytvorili obsah.)"

    simulation_outcome: dict[str, Any] | None
    if sandbox_requested:
        simulation_outcome = {"probes": sandbox_probes}
    else:
        simulation_outcome = None

    await _fanout_transcript(session_id, orch.name, "Orchestrator + Review lane: zápis reflexie.")

    reflection_excerpt = ""
    post_meta = await run_ballroom_post_mortem_persistence(
        session,
        settings=settings,
        orchestrator_prompt=orch_system,
        preview_digest=breaker_digest_text,
        user_brief=brief,
        stitched_deliverables=stitched,
        manager_template_slugs=selected_slugs,
        mission_id=mission_id,
        session_id=session_id,
        orchestrator_agent_id=orch.id,
    )
    reflection_excerpt = str(post_meta.get("reflection_excerpt") or "").strip()

    await _fanout_transcript(session_id, orch.name, "Zostavujem finálny report a hlasové zhrnutie.")

    voice_script = stitched[:2400]
    final_markdown = stitched.strip()
    reflection_block = (
        f"\n\n### Post-mortem excerpt\n{reflection_excerpt[:6000]}" if reflection_excerpt else ""
    )

    structured_bundle = build_fallback_structured(
        brief_excerpt=brief,
        manager_slugs=selected_slugs,
        post_meta=post_meta,
    )

    orch_json_extra: dict[str, object] = {}

    if hive_llm_credentials_ready():
        orch_raw_bundle, _v_cost = await _llm_router_text(
            session,
            system_prompt=orch_system,
            user_payload=(
                "Produce THREE sections exactly:\n"
                "SECTION_TEXT: (Markdown executive report)\n"
                "SECTION_JSON: (single compact JSON object with optional keys summary, artefacts, timeline, checklist)\n"
                "SECTION_VOICE: (Spoken narration under ~120 words, plain text, no bullets)\n\n"
                "## Manager bundle\n"
                f"{stitched[:12_000]}\n\n## Reflection + lessons\n"
                f"{reflection_block[:8000] or '(reflection unavailable)'}\n\n"
                "## Original brief\n"
                f"{brief[:4000]}\n"
            ),
            swarm_id=str(session_id),
            task_slug=f"orch_final-{mission_id}",
        )
        orch_sections = split_orchestrator_deliverable_sections(orch_raw_bundle)
        if orch_sections.get("text"):
            final_markdown = str(orch_sections["text"]).strip()
        sj = coalesce_json_text(orch_sections.get("json"))
        orch_json_extra = sj
        if orch_sections.get("voice"):
            voice_script = str(orch_sections["voice"]).strip()

    structured_bundle.update(orch_json_extra)

    await _fanout_orchestrator_delivery(
        session_id=session_id,
        orchestrator_label=orch.name,
        text_report=final_markdown,
        voice_script=voice_script,
    )

    tag_candidates = [
        *selected_slugs,
        "hive.mission",
        "phase0_51.archive",
        "phase0_6.hive_mind",
        *(
            ["personal"]
            if any(k in brief.lower() for k in ("life", "habit", "calendar", "wellness"))
            else []
        ),
        *(
            ["marketing"]
            if any(k in brief.lower() for k in ("marketing", "campaign", "linkedin", "newsletter"))
            else []
        ),
        *(["engineering"] if any(k in brief.lower() for k in ("deploy", "code", "github")) else []),
    ]
    inferred_tags = sorted(dict.fromkeys(tag_candidates))

    finalized = await OutputEngine.create_final_deliverable(
        session,
        lineage_id=mission_id,
        markdown_body=final_markdown,
        structured=dict(structured_bundle),
        title_hint=(final_markdown.splitlines()[0] if final_markdown else brief)[:200],
        slug_hint=slugify_fragment(brief[:120]),
        tags=list(inferred_tags),
        voice_script=voice_script,
        dashboard_user_id=parse_dashboard_user_subject(hive_subject),
        ballroom_session_id=session_id,
        mission_id=mission_id,
        source_task_id=None,
        settings=settings,
        hive_mind_extras=HiveMindExtras(reflection_excerpt=reflection_excerpt or None, manager_template_slugs=selected_slugs),
    )

    dash_uid = parse_dashboard_user_subject(hive_subject)
    payload_meta: dict[str, Any] = {
        "mission_id": str(mission_id),
        "session_id": str(session_id),
        "orchestrator_id": str(orch.id),
        "manager_template_slugs": selected_slugs,
        "managers_used": [],
        "status": "delivered_via_orchestrator",
        "user_brief_excerpt": brief[:500],
        "post_mortem": post_meta,
        "final_deliverable_id": str(finalized.id),
        "deliverable_lineage_id": str(finalized.lineage_id),
        "deliverable_version": finalized.version,
    }

    await _fanout_transcript(
        session_id,
        orch.name,
        f"✅ Task completed — Final deliverable ready (v{finalized.version}). Outputs tab: /outputs · id={finalized.id}",
    )

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

    mission_task_row = await session.get(Task, mission_id)
    if mission_task_row is not None:
        mission_task_row.status = TaskStatus.COMPLETED
        mission_task_row.completed_at = datetime.now(tz=UTC)
        await session.flush()

    return {
        "mission_id": str(mission_id),
        "session_id": str(session_id),
        "orchestrator": str(orch.id),
        "manager_template_slugs": selected_slugs,
        "managers_used": [],
        "post_mortem": post_meta,
        "final_deliverable_id": str(finalized.id),
        "deliverable_version": finalized.version,
        "status": "delivered_via_orchestrator",
        "hive_subject": hive_subject,
    }
