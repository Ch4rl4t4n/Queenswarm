"""Unified Operator Control Plane — compose existing subsystems without duplicating logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.tenant import Tenant

TrustLane = Literal["auto", "simulate", "live"]
OperatorLoopPhase = Literal["morning", "evening", "anytime"]


class OperatorLoopActionOut(BaseModel):
    """One actionable next step for the operator loop panel."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: Literal["high", "medium", "low"]
    href: str | None = None


class OperatorLoopSnapshotOut(BaseModel):
    """Morning/evening loop snapshot composed from optional subsystems."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    phase: OperatorLoopPhase
    overnight: dict[str, Any] = Field(default_factory=dict)
    morning_brief: dict[str, Any] = Field(default_factory=dict)
    publish_pipeline: dict[str, Any] = Field(default_factory=dict)
    publish_onboarding: dict[str, Any] = Field(default_factory=dict)
    trading: dict[str, Any] = Field(default_factory=dict)
    actions: list[OperatorLoopActionOut] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


async def _compose_operator_loop_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    phase: OperatorLoopPhase,
) -> OperatorLoopSnapshotOut:
    """Compose loop snapshot when the full Operator Loop module is deployed."""

    try:
        from app.application.services.operator_loop import compose_operator_loop_snapshot

        return await compose_operator_loop_snapshot(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            phase=phase,
        )
    except ModuleNotFoundError:
        return OperatorLoopSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            phase=phase,
            actions=[
                OperatorLoopActionOut(
                    id="open_cockpit",
                    label="Open Hive Cockpit",
                    detail="Operator Loop module not deployed — use Cockpit actions.",
                    priority="medium",
                    href="/cockpit",
                ),
            ],
        )


async def _get_solo_trio_status(db: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Return solo trio status when module is available."""

    try:
        from app.application.services.solo_operator_trio import get_solo_trio_status

        return await get_solo_trio_status(db, tenant_id=tenant_id)
    except ModuleNotFoundError:
        return {"enabled": False, "reason": "solo_operator_trio_not_deployed"}


async def _compose_solo_daily_plan(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    max_items: int,
) -> BaseModel:
    """Return daily plan snapshot when module is available."""

    try:
        from app.application.services.solo_daily_plan import compose_solo_daily_plan

        return await compose_solo_daily_plan(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            max_items=max_items,
        )
    except ModuleNotFoundError:
        from pydantic import BaseModel as PydanticBaseModel

        class _EmptyDailyPlan(PydanticBaseModel):
            enabled: bool = False
            items: list[dict[str, Any]] = Field(default_factory=list)

        return _EmptyDailyPlan()


FEATURE_MODULE_IDS: tuple[str, ...] = (
    "bee_hotline",
    "trust_autopilot",
    "factory_spark",
    "hive_oracle",
    "context_teleport",
    "regret_simulator",
    "swarm_immune_system",
    "intent_crystallizer",
    "evolutionary_recipes",
    "ambient_forager",
    "parallel_hive_view",
    "zero_ui_mode",
    "proof_of_hive",
    "hive_innovation_lab",
)


class OperatorCockpitActionOut(BaseModel):
    """Prioritized action for the unified cockpit."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: Literal["high", "medium", "low"]
    href: str | None = None
    action: str | None = None


class SwarmFleetItemOut(BaseModel):
    """Always-on routine row for Trust Autopilot fleet view."""

    model_config = ConfigDict(extra="ignore")

    routine_id: str
    name: str
    active: bool
    schedule_kind: str
    autopilot: bool
    next_run_at: str | None = None
    wizard_template: str | None = None
    immune_status: Literal["healthy", "watch", "quarantine"] = "healthy"


class FeatureModuleOut(BaseModel):
    """One futurist capability exposed in the control plane."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    status: Literal["live", "beta", "planned"]
    summary: str
    enabled: bool = True


class OperatorCockpitSnapshotOut(BaseModel):
    """Single snapshot for Operator Control Plane UI and messaging gateways."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    phase: Literal["morning", "evening", "anytime"]
    now_actions: list[OperatorCockpitActionOut] = Field(default_factory=list)
    swarm_fleet: list[SwarmFleetItemOut] = Field(default_factory=list)
    trio: dict[str, Any] = Field(default_factory=dict)
    daily_plan: dict[str, Any] = Field(default_factory=dict)
    oracle_warnings: list[dict[str, str]] = Field(default_factory=list)
    feature_modules: list[FeatureModuleOut] = Field(default_factory=list)
    innovation_lab: dict[str, Any] = Field(default_factory=dict)
    zero_ui: dict[str, Any] = Field(default_factory=dict)
    trust_autopilot: dict[str, Any] = Field(default_factory=dict)
    proof_of_hive: dict[str, Any] = Field(default_factory=dict)
    hive_oracle: dict[str, Any] = Field(default_factory=dict)
    intent_crystallizer: dict[str, Any] = Field(default_factory=dict)
    links: dict[str, str] = Field(default_factory=dict)
    operator_loop: dict[str, Any] = Field(default_factory=dict)


class OperatorContextOut(BaseModel):
    """Unified operator memory inject for Queen / supervisor bootstrap."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    soul_excerpt: str = ""
    user_instructions_excerpt: str = ""
    mission_excerpt: str = ""
    prompt_prefix: str = ""
    char_count: int = 0


class OperatorActRequest(BaseModel):
    """Typed operator action routed to existing services."""

    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "start_day",
        "run_trio",
        "hotline",
        "factory_spark",
        "crystallize_intent",
        "pause_routine",
        "resume_routine",
        "run_routine_now",
    ]
    text: str | None = Field(default=None, max_length=8000)
    routine_id: uuid.UUID | None = None
    trust_lane: TrustLane | None = None


class OperatorActResultOut(BaseModel):
    """Result of a control-plane action."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    action: str
    message: str
    trust_lane: TrustLane = "simulate"
    href: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def _feature_modules_catalog() -> list[FeatureModuleOut]:
    """Static catalog of control-plane capabilities (compose-only, no new bees)."""

    enabled = bool(settings.operator_control_plane_enabled)
    return [
        FeatureModuleOut(
            id="bee_hotline",
            label="Bee Hotline",
            status="beta",
            summary="One line routes to the right specialist bee or swarm.",
            enabled=enabled,
        ),
        FeatureModuleOut(
            id="trust_autopilot",
            label="Trust Autopilot",
            status="beta",
            summary="Always-on routines ping only verified outcomes.",
            enabled=enabled and settings.operator_zero_ui_notify_enabled,
        ),
        FeatureModuleOut(
            id="factory_spark",
            label="Factory Spark",
            status="beta",
            summary="One sentence → Micro-SaaS Factory verified launch pack.",
            enabled=enabled and settings.micro_saas_factory_enabled,
        ),
        FeatureModuleOut(
            id="hive_oracle",
            label="Hive Oracle",
            status="live",
            summary="Predictive warnings before swarm failure.",
            enabled=enabled and settings.hive_oracle_enabled,
        ),
        FeatureModuleOut(
            id="context_teleport",
            label="Context Teleport",
            status="planned",
            summary="1-click verified context between swarms.",
            enabled=enabled and settings.cross_swarm_knowledge_enabled,
        ),
        FeatureModuleOut(
            id="regret_simulator",
            label="Regret Simulator",
            status="planned",
            summary="Pre-mortem score before live publish or trading.",
            enabled=enabled,
        ),
        FeatureModuleOut(
            id="swarm_immune_system",
            label="Swarm Immune System",
            status="beta",
            summary="Quarantine failing routines; suggest imitation failover.",
            enabled=enabled,
        ),
        FeatureModuleOut(
            id="intent_crystallizer",
            label="Intent Crystallizer",
            status="live",
            summary="Free text → goal + swarm template + trust lane.",
            enabled=enabled and settings.intent_crystallizer_enabled,
        ),
        FeatureModuleOut(
            id="evolutionary_recipes",
            label="Evolutionary Recipes",
            status="beta",
            summary="Verified recipe variants compete on pollen fitness.",
            enabled=enabled and settings.imitation_v2_enabled,
        ),
        FeatureModuleOut(
            id="ambient_forager",
            label="Ambient Forager",
            status="planned",
            summary="Passive ingest → morning relevance brief.",
            enabled=enabled and getattr(settings, "forager_intelligence_enabled", True),
        ),
        FeatureModuleOut(
            id="parallel_hive_view",
            label="Parallel Hive View",
            status="planned",
            summary="Mission control for multi-bee sessions.",
            enabled=enabled,
        ),
        FeatureModuleOut(
            id="zero_ui_mode",
            label="Zero-UI Hive Mode",
            status="beta",
            summary="Telegram priority pings — web optional.",
            enabled=enabled and settings.operator_telegram_inbound_enabled,
        ),
        FeatureModuleOut(
            id="proof_of_hive",
            label="Proof-of-Hive",
            status="beta",
            summary="Shareable verify receipt per artifact.",
            enabled=enabled and settings.proof_of_hive_enabled,
        ),
        FeatureModuleOut(
            id="hive_innovation_lab",
            label="Hive Innovation Lab",
            status="live",
            summary="Brainstorm features → approve → auto-implement via Maintainer.",
            enabled=enabled and settings.hive_innovation_lab_enabled,
        ),
    ]


async def _load_swarm_fleet(db: AsyncSession, *, tenant_id: uuid.UUID) -> list[SwarmFleetItemOut]:
    """List supervisor routines as always-on swarm fleet rows."""

    rows = list(
        (
            await db.scalars(
                select(SupervisorRoutine)
                .where(SupervisorRoutine.tenant_id == tenant_id)
                .order_by(desc(SupervisorRoutine.is_active), desc(SupervisorRoutine.updated_at))
                .limit(24),
            )
        ).all(),
    )
    fleet: list[SwarmFleetItemOut] = []
    for row in rows:
        payload = dict(row.context_payload or {})
        immune = "healthy"
        failures = int(payload.get("consecutive_failures") or 0)
        if failures >= 3:
            immune = "quarantine"
        elif failures >= 1:
            immune = "watch"
        fleet.append(
            SwarmFleetItemOut(
                routine_id=str(row.id),
                name=str(row.name),
                active=bool(row.is_active),
                schedule_kind=str(row.schedule_kind),
                autopilot=bool(row.is_active and row.schedule_kind in {"cron", "interval"}),
                next_run_at=row.next_run_at.isoformat() if row.next_run_at else None,
                wizard_template=str(payload.get("wizard_template") or "") or None,
                immune_status=immune,
            ),
        )
    return fleet


def _derive_oracle_warnings(
    *,
    loop_actions: list[OperatorLoopActionOut],
    fleet: list[SwarmFleetItemOut],
    trio: dict[str, Any],
) -> list[dict[str, str]]:
    """Legacy wrapper — delegates to Hive Oracle v2 heuristics."""

    from app.application.services.hive_oracle import _warning_dicts, derive_heuristic_warnings

    warnings = derive_heuristic_warnings(
        loop_actions=loop_actions,
        fleet=fleet,
        trio=trio,
    )
    return _warning_dicts(warnings)


def _cockpit_actions_from_loop(actions: list[OperatorLoopActionOut]) -> list[OperatorCockpitActionOut]:
    """Map operator loop actions and prepend start_day."""

    out: list[OperatorCockpitActionOut] = [
        OperatorCockpitActionOut(
            id="start_day",
            label="Spusti deň",
            detail="Trio cycle + morning brief pipeline (verify-first).",
            priority="high",
            action="start_day",
        ),
    ]
    for row in actions[:4]:
        out.append(
            OperatorCockpitActionOut(
                id=row.id,
                label=row.label,
                detail=row.detail,
                priority=row.priority,
                href=row.href,
                action=None,
            ),
        )
    return out[:5]


async def compose_operator_cockpit_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    phase: Literal["morning", "evening", "anytime"] = "morning",
) -> OperatorCockpitSnapshotOut:
    """Assemble unified control plane from existing verified subsystems."""

    if not settings.operator_control_plane_enabled:
        return OperatorCockpitSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            phase=phase,
        )

    loop = await _compose_operator_loop_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        phase=phase,
    )
    trio = await _get_solo_trio_status(db, tenant_id=tenant_id)
    daily = await _compose_solo_daily_plan(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        max_items=5,
    )
    fleet = await _load_swarm_fleet(db, tenant_id=tenant_id)

    innovation_pending = 0
    if settings.hive_innovation_lab_enabled:
        from app.application.services.hive_innovation_lab import count_pending_innovation_proposals

        innovation_pending = await count_pending_innovation_proposals(db, tenant_id=tenant_id)

    from app.application.services.hive_oracle import _warning_dicts, compose_hive_oracle_snapshot
    from app.application.services.intent_crystallizer import compose_intent_crystallizer_snapshot
    from app.application.services.operator_telegram_gateway import compose_zero_ui_status
    from app.application.services.proof_of_hive import compose_recent_proof_receipts

    oracle_snap = await compose_hive_oracle_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        loop_actions=loop.actions,
        fleet=fleet,
        trio=trio,
        loop=loop.model_dump(mode="json"),
        innovation_pending=innovation_pending,
        include_synthesis=False,
    )
    oracle = _warning_dicts(oracle_snap.warnings)

    zero_ui = compose_zero_ui_status(tenant=tenant)
    proofs = compose_recent_proof_receipts(tenant, limit=6)

    return OperatorCockpitSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        phase=phase,
        now_actions=_cockpit_actions_from_loop(loop.actions),
        swarm_fleet=fleet,
        trio=trio,
        daily_plan=daily.model_dump(mode="json"),
        oracle_warnings=oracle,
        feature_modules=_feature_modules_catalog(),
        innovation_lab={
            "enabled": settings.hive_innovation_lab_enabled,
            "pending_count": innovation_pending,
            "href_brainstorm": "/cockpit#innovation-lab",
        },
        zero_ui=zero_ui.model_dump(mode="json"),
        trust_autopilot={
            "enabled": settings.operator_zero_ui_notify_enabled,
            "lanes": {
                "simulate_ready": "🟡 publish queue + social simulate",
                "live_gate": "🔴 live confirm required",
                "verified_info": "🟢 approved / auto-live",
            },
        },
        proof_of_hive=proofs.model_dump(mode="json"),
        hive_oracle={
            **oracle_snap.model_dump(mode="json"),
            "href_full": "/oracle",
        },
        intent_crystallizer=compose_intent_crystallizer_snapshot().model_dump(mode="json"),
        operator_loop=loop.model_dump(mode="json"),
        links={
            "cockpit": "/cockpit",
            "oracle": "/oracle",
            "advanced_dashboard": "/dashboard",
            "agents": "/agents",
            "swarms": "/swarms",
            "factory": "/factory",
            "ballroom": "/ballroom",
            "knowledge": "/knowledge",
            "execution_studio": "/integrations?tab=studio",
            "settings_harness": "/settings/harness",
        },
    )


async def compose_operator_context(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> OperatorContextOut:
    """Unified brain pack digest for session bootstrap."""

    if not settings.operator_control_plane_enabled:
        return OperatorContextOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    service = CuratedMemoryService(db=db)
    bundle = await service.get_bundle(tenant_id)
    prefix = service.render_prompt_prefix(bundle)
    from app.domain.memory.curated import CuratedFileKind

    soul_text = bundle.get(CuratedFileKind.SOUL, "")[:600]
    user_text = bundle.get(CuratedFileKind.INSTRUCTIONS, "")[:600]
    mission_text = bundle.get(CuratedFileKind.MISSION, "")[:400]
    return OperatorContextOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        soul_excerpt=soul_text,
        user_instructions_excerpt=user_text,
        mission_excerpt=mission_text,
        prompt_prefix=prefix[:4000],
        char_count=len(prefix),
    )


def _resolve_trust_lane(*, action: str, explicit: TrustLane | None) -> TrustLane:
    if explicit is not None:
        return explicit
    if action in {"start_day", "run_trio", "crystallize_intent", "hotline"}:
        return "auto"
    if action in {"factory_spark", "run_routine_now"}:
        return "simulate"
    return "simulate"


def _crystallize_intent(text: str) -> dict[str, Any]:
    """Legacy dict wrapper for Intent Crystallizer v2."""

    from app.application.services.intent_crystallizer import crystallize_intent

    return crystallize_intent(text).model_dump(mode="json")


async def execute_operator_action(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    reviewer_subject: str,
    body: OperatorActRequest,
) -> OperatorActResultOut:
    """Route control-plane action to existing services — no duplicated business logic."""

    if not settings.operator_control_plane_enabled:
        return OperatorActResultOut(
            ok=False,
            action=body.action,
            message="Operator Control Plane disabled.",
        )

    lane = _resolve_trust_lane(action=body.action, explicit=body.trust_lane)

    if body.action == "start_day":
        try:
            from app.application.services.solo_operator_trio import run_solo_trio_cycle
        except ModuleNotFoundError:
            return OperatorActResultOut(
                ok=False,
                action=body.action,
                message="Solo trio module not deployed.",
                trust_lane="auto",
            )

        trio_result = await run_solo_trio_cycle(db, tenant_id=tenant_id)
        return OperatorActResultOut(
            ok=True,
            action=body.action,
            message="Morning trio cycle triggered.",
            trust_lane="auto",
            payload=trio_result,
            href="/agents",
        )

    if body.action == "run_trio":
        try:
            from app.application.services.solo_operator_trio import run_solo_trio_cycle
        except ModuleNotFoundError:
            return OperatorActResultOut(
                ok=False,
                action=body.action,
                message="Solo trio module not deployed.",
                trust_lane="auto",
            )

        result = await run_solo_trio_cycle(db, tenant_id=tenant_id)
        return OperatorActResultOut(
            ok=True,
            action=body.action,
            message="Trio cycle triggered.",
            trust_lane="auto",
            payload=result,
        )

    if body.action in {"hotline", "factory_spark", "crystallize_intent"}:
        text = (body.text or "").strip()
        if not text:
            return OperatorActResultOut(
                ok=False,
                action=body.action,
                message="text is required for this action.",
            )
        plan_raw = _crystallize_intent(text)
        if body.action == "crystallize_intent":
            return OperatorActResultOut(
                ok=True,
                action=body.action,
                message="Intent crystallized.",
                trust_lane=plan_raw["trust_lane"],
                payload=plan_raw,
                href=plan_raw.get("primary_href") or "/cockpit#intent-crystallizer",
            )

        from app.application.services.intent_crystallizer import (
            IntentCrystallizerPlanOut,
            launch_crystallized_intent,
        )

        plan = IntentCrystallizerPlanOut.model_validate(plan_raw)
        launched = await launch_crystallized_intent(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            reviewer_subject=reviewer_subject,
            plan=plan,
            spawn_factory=body.action == "factory_spark",
        )

        if launched.get("requires_confirm"):
            return OperatorActResultOut(
                ok=False,
                action=body.action,
                message="Live lane requires explicit operator confirm in Advanced UI.",
                trust_lane="live",
                payload=launched,
                href="/integrations?tab=studio",
            )

        return OperatorActResultOut(
            ok=True,
            action=body.action,
            message="Bee Hotline routed to Queen goal (verify-first).",
            trust_lane=plan.trust_lane,
            payload=launched,
            href=str(launched.get("href") or plan.primary_href),
        )

    if body.action in {"pause_routine", "resume_routine", "run_routine_now"}:
        if body.routine_id is None:
            return OperatorActResultOut(ok=False, action=body.action, message="routine_id required.")
        routine = await db.get(SupervisorRoutine, body.routine_id)
        if routine is None or routine.tenant_id != tenant_id:
            return OperatorActResultOut(ok=False, action=body.action, message="Routine not found.")
        if body.action == "pause_routine":
            routine.is_active = False
            await db.flush()
            return OperatorActResultOut(
                ok=True,
                action=body.action,
                message=f"Paused routine {routine.name}.",
                trust_lane="auto",
            )
        if body.action == "resume_routine":
            routine.is_active = True
            await db.flush()
            return OperatorActResultOut(
                ok=True,
                action=body.action,
                message=f"Resumed routine {routine.name}.",
                trust_lane="auto",
            )
        from app.application.services.supervisor.routine_service import trigger_supervisor_routine_now

        session_id = await trigger_supervisor_routine_now(db, routine=routine)
        return OperatorActResultOut(
            ok=True,
            action=body.action,
            message=f"Triggered routine {routine.name}.",
            trust_lane="simulate",
            payload={"session_id": str(session_id)},
            href=f"/agents?session={session_id}",
        )

    return OperatorActResultOut(ok=False, action=body.action, message="Unknown action.")


__all__ = [
    "FEATURE_MODULE_IDS",
    "OperatorActRequest",
    "OperatorActResultOut",
    "OperatorCockpitSnapshotOut",
    "OperatorContextOut",
    "compose_operator_cockpit_snapshot",
    "compose_operator_context",
    "execute_operator_action",
]
