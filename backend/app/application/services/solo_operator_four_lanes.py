"""Four-lane solo operator model — parallel missions with one control surface.

Replaces sprawl from generic Virtual Company bootstrap with four explicit lanes:
marketing (Najman), tech SCV, e-shop research, and automation (approve-only).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_service import ForagerService
from app.application.services.queen_maintainer.service import ensure_queen_maintainer_routine
from app.application.services.supervisor.routine_service import create_supervisor_routine
from app.core.logging import get_logger
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

logger = get_logger(__name__)

FourLaneId = Literal["marketing_najman", "tech_scv", "eshop_research", "automation"]

FOUR_LANE_IDS: tuple[FourLaneId, ...] = (
    "marketing_najman",
    "tech_scv",
    "eshop_research",
    "automation",
)

FOUR_LANE_PAYLOAD_KEY = "four_lane_id"

# Canonical routine display names (idempotent match).
LANE_ROUTINE_NAMES: dict[FourLaneId, str] = {
    "marketing_najman": "Four Lane · Najman marketing digest",
    "tech_scv": "Four Lane · Tech SCV upgrade digest",
    "eshop_research": "Four Lane · E-shop research digest",
    "automation": "Four Lane · Automation queue",
}

# Legacy routines paused during bootstrap (exact or prefix match, case-insensitive).
LEGACY_ROUTINE_PAUSE_PATTERNS: tuple[str, ...] = (
    "memory dreaming",
    "overnight dump",
    "sentinel daily scan",
    "forager · x intel",
    "forager · youtube intel",
    "daily sales waterfall",
    "digital ops review",
    "e-shop ops tick",
    "marketing ops cycle",
    "r&d weekly scan",
    "weekly ship review",
    "bank po weekly brief",
    "weekly finance snapshot",
    "life os morning briefing",
)

# Retag these existing names into four-lane routines instead of duplicating.
LEGACY_ROUTINE_RETAG: dict[str, FourLaneId] = {
    "marketing ops cycle": "marketing_najman",
    "sentinel · upgrade backlog": "tech_scv",
}

LANE_ROUTINE_GOALS: dict[FourLaneId, str] = {
    "marketing_najman": """\
Four Lane A — Najman marketing digest (CZ, simulate-first).

Kontext: firm_id=najman · Rodinné včelařství Najman · vcelarstvinajman.cz · beebrdy.cz · rozvozmedu.cz
Použij curated memory „Najman Marketing Colony“ a forager „Vcelarstvi Competitor Intel“.

Úkol:
1. Z posledních 72 h HiveMind/forager signálů vyber top 5 insightů pro marketing.
2. SWOT fragment (1 silná stránka, 1 riziko, 1 příležitost) vs CZ/SK konkurence.
3. 3 návrhy obsahu (IG/FB/blog) s hookem a CTA — simulate only.
4. 1 konkrétní návrh tasku/automatizace (routine nebo publish queue) — operator schvaluje.

Výstup: operator_reply v češtině, max 400 slov, strukturované bullets.
Ulož verified brief do HiveMind tagy: najman-marketing, four-lane, digest.
Critic APPROVE před reportem. Žádný live publish.
""".strip(),
    "tech_scv": """\
Four Lane B — Tech SCV upgrade digest (Queenswarm platform).

Sken posledních 24 h: forager intel (X/YouTube tech), GitHub releases, harness docs.
Produkc EXACTLY 3 návrhy vylepšení swarmu:
- title (5–9 slov)
- type: new_mcp | new_model | new_library | deprecated | cost_saver | ux
- rationale (2 věty, evidence)
- expected_impact: low | medium | high
- effort_hours (integer)
- evidence_link nebo HiveMind ref

Každý návrh připrav jako Innovation Lab proposal draft v simulate režimu.
operator_reply: 3 bullets SK. Critic verify před odesláním.
Tag: four-lane, tech-scv, upgrade-candidate.
""".strip(),
    "eshop_research": """\
Four Lane C — E-shop research digest (beebrdy.cz · WooCommerce).

Kontext: firm_id=najman · eshop beebrdy.cz · platby Comgate/GoPay plánovány · simulate-first.

Úkol:
1. Konkurenční benchmark 3 CZ/SK včelařských e-shopů (UX, checkout, produktové stránky).
2. 5 konkrétních UX/conversion hypotéz pro beebrdy.cz.
3. Keyword cluster pro produktové kategorie medu (CZ).
4. 2 návrhy A/B testů (simulate) + 1 task pro operátora.

Výstup v češtině, max 350 slov. Tag: najman-eshop, four-lane, eshop-research.
Critic APPROVE. Žádné live změny webu.
""".strip(),
    "automation": """\
Four Lane D — Automation queue (manual trigger only).

Tato rutina se nespouští automaticky — operátor ji volá po schválení návrhů z lane A/B/C.

Úkol:
1. Načti schválené AgentSuggestion / Innovation Lab návrhy se statusem approved.
2. Pro každý: navrhni SupervisorRoutine nebo Task s goal template, schedule, guardrails.
3. Tech implementace → odkaž na Queen Maintainer (PR-only).
4. Marketing publish → simulate queue, operator approval gate.

Výstup: checklist max 5 položek SK. simulate-first vždy.
""".strip(),
}

LANE_CRON: dict[FourLaneId, str | None] = {
    "marketing_najman": "0 9 * * 1,3,5",
    "tech_scv": "30 7 * * *",
    "eshop_research": "0 10 * * 2,4",
    "automation": None,
}

LANE_FORAGER_NAMES: dict[FourLaneId, tuple[str, ...]] = {
    "marketing_najman": ("Vcelarstvi Competitor Intel",),
    "tech_scv": ("X Intel", "YouTube Intel"),
    "eshop_research": ("Najman E-shop Intel",),
    "automation": (),
}

ESHOP_FORAGER_SPEC: dict[str, Any] = {
    "name": "Najman E-shop Intel",
    "description": "CZ/SK včelařské e-shopy — RSS/product signals pro beebrdy.cz research lane.",
    "source_type": "rss",
    "source_config": {
        "feeds": [
            "https://www.pleva.cz/blog/rss",
            "https://www.jahan.cz/rss",
            "https://www.trebonsky-med.cz/feed/",
        ],
        "fallback_site_urls": [
            "https://www.pleva.cz/",
            "https://www.jahan.cz/",
            "https://www.trebonsky-med.cz/",
            "https://www.vceliobchod.cz/",
            "https://www.ivcelarskepotreby.sk/",
        ],
    },
    "schedule_cron": "0 6 * * 2,4",
    "is_active": True,
}


class FourLaneRoutineOut(BaseModel):
    """One bound routine for a four-lane mission."""

    model_config = ConfigDict(extra="ignore")

    lane_id: FourLaneId
    routine_id: str | None = None
    routine_name: str | None = None
    is_active: bool = False
    schedule_cron: str | None = None
    last_session_id: str | None = None
    last_session_status: str | None = None
    last_run_at: datetime | None = None


class FourLaneForagerOut(BaseModel):
    """Forager associated with a lane."""

    model_config = ConfigDict(extra="ignore")

    lane_id: FourLaneId
    forager_id: str | None = None
    name: str | None = None
    is_active: bool = False
    items_count: int = 0


class FourLaneOut(BaseModel):
    """Single lane card for operator UI."""

    model_config = ConfigDict(extra="ignore")

    lane_id: FourLaneId
    label: str
    description: str
    operator_hint: str
    manual_anchor: str
    routine: FourLaneRoutineOut
    foragers: list[FourLaneForagerOut] = Field(default_factory=list)
    open_href: str
    open_label: str
    pending_digest_count: int = 0
    promote_ready_count: int = 0
    first_promote_session_id: str | None = None
    # Deprecated aliases — kept for older clients
    approve_href: str = ""
    sessions_href: str = ""


class FourLaneSnapshotOut(BaseModel):
    """Full four-lane control plane snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    lanes: list[FourLaneOut] = Field(default_factory=list)
    legacy_paused_count: int = 0
    active_lane_count: int = 0


LANE_META: dict[FourLaneId, dict[str, str]] = {
    "marketing_najman": {
        "label": "Najman Marketing",
        "description": "Annual campaign — competitor intel, CZ digest, simulate-first publish.",
        "operator_hint": "Mon/Wed/Fri 9:00 digest · approve in Digest Inbox below → Tasks.",
        "manual_anchor": "four-lanes-marketing",
        "open_href": "/agents#sessions",
        "open_label": "Sessions",
    },
    "tech_scv": {
        "label": "Tech SCV",
        "description": "Daily platform improvement proposals → Innovation Lab → Maintainer PR.",
        "operator_hint": "Daily 7:30 digest · review proposals in Innovation Lab (not Approve on this card).",
        "manual_anchor": "four-lanes-tech",
        "open_href": "/integrations?tab=studio&section=innovation#innovation-lab",
        "open_label": "Innovation Lab",
    },
    "eshop_research": {
        "label": "E-shop Research",
        "description": "beebrdy.cz benchmark, UX hypotheses, SEO clusters.",
        "operator_hint": "Tue/Thu 10:00 digest · approve in Digest Inbox below → redesign brief.",
        "manual_anchor": "four-lanes-eshop",
        "open_href": "/knowledge#hivemind",
        "open_label": "HiveMind",
    },
    "automation": {
        "label": "Automation Factory",
        "description": "Approved proposals → routines, tasks, Maintainer — manual trigger only.",
        "operator_hint": "Run after approving marketing/e-shop digests · no auto-cron.",
        "manual_anchor": "four-lanes-automation",
        "open_href": "/tasks",
        "open_label": "Tasks",
    },
}


def _lane_from_payload(context_payload: dict[str, Any] | None) -> FourLaneId | None:
    if not isinstance(context_payload, dict):
        return None
    raw = context_payload.get(FOUR_LANE_PAYLOAD_KEY)
    if raw is None:
        return None
    lane = str(raw).strip().lower()
    if lane in FOUR_LANE_IDS:
        return lane  # type: ignore[return-value]
    return None


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _retag_lane_for_name(name: str) -> FourLaneId | None:
    normalized = _normalize_name(name)
    for pattern, lane_id in LEGACY_ROUTINE_RETAG.items():
        if pattern in normalized:
            return lane_id
    return None


async def _load_tenant_routines(db: AsyncSession, *, tenant_id: uuid.UUID) -> list[SupervisorRoutine]:
    return list(
        (
            await db.scalars(
                select(SupervisorRoutine)
                .where(SupervisorRoutine.tenant_id == tenant_id)
                .order_by(SupervisorRoutine.name.asc()),
            )
        ).all(),
    )


async def _tag_routine_lane(
    db: AsyncSession,
    *,
    routine: SupervisorRoutine,
    lane_id: FourLaneId,
) -> None:
    payload = dict(routine.context_payload or {})
    payload[FOUR_LANE_PAYLOAD_KEY] = lane_id
    payload["solo_operator_four_lane"] = True
    payload["simulate_first"] = True
    payload.pop("routine_kind", None)
    routine.context_payload = payload


async def _ensure_lane_routine(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lane_id: FourLaneId,
    routines: list[SupervisorRoutine],
    created_by_subject: str | None,
) -> tuple[SupervisorRoutine, str]:
    """Create or retag a lane routine; return (row, action)."""

    canonical = LANE_ROUTINE_NAMES[lane_id]
    existing: SupervisorRoutine | None = None
    for row in routines:
        if _is_queen_maintainer_routine(row.name):
            continue
        if _lane_from_payload(dict(row.context_payload or {})) == lane_id:
            existing = row
            break
        if _normalize_name(row.name) == _normalize_name(canonical):
            existing = row
            break
        retag = _retag_lane_for_name(row.name)
        if retag == lane_id and existing is None:
            existing = row

    if existing is None:
        cron = LANE_CRON[lane_id]
        schedule_kind = "interval" if cron is None else "cron"
        row = await create_supervisor_routine(
            db,
            name=canonical,
            goal_template=LANE_ROUTINE_GOALS[lane_id],
            created_by_subject=created_by_subject,
            schedule_kind=schedule_kind,
            interval_seconds=604800 if cron is None else None,
            cron_expr=cron,
            runtime_mode="durable",
            roles=["researcher", "critic"],
            retrieval_contract="default_v2",
            skills=["context", "execution-studio", "marketing-campaign-playbook"]
            if lane_id == "marketing_najman"
            else ["context", "execution-studio", "queen-maintainer"]
            if lane_id == "tech_scv"
            else ["context", "execution-studio"],
            context_payload={
                FOUR_LANE_PAYLOAD_KEY: lane_id,
                "solo_operator_four_lane": True,
                "simulate_first": True,
            },
            tenant_id=tenant_id,
        )
        if lane_id == "automation":
            row.is_active = False
        await db.flush()
        return row, "created"

    await _tag_routine_lane(db, routine=existing, lane_id=lane_id)
    if existing.name != canonical and _normalize_name(existing.name) != _normalize_name(canonical):
        existing.name = canonical
    existing.goal_template = LANE_ROUTINE_GOALS[lane_id]
    expected_roles = ["researcher", "critic"]
    if lane_id != "automation" and list(existing.roles or []) != expected_roles:
        existing.roles = expected_roles
    existing.runtime_mode = "durable"
    expected_skills = (
        ["context", "execution-studio", "marketing-campaign-playbook"]
        if lane_id == "marketing_najman"
        else ["context", "execution-studio", "queen-maintainer"]
        if lane_id == "tech_scv"
        else ["context", "execution-studio"]
    )
    if lane_id != "automation" and list(existing.skills or []) != expected_skills:
        existing.skills = expected_skills
    cron = LANE_CRON[lane_id]
    if cron is not None:
        existing.schedule_kind = "cron"
        existing.cron_expr = cron
    if lane_id == "automation":
        existing.is_active = False
    else:
        existing.is_active = True
    await db.flush()
    return existing, "updated"


async def _reactivate_lane_forager_routines(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[str]:
    """Re-enable evaluator routines for foragers bound to four lanes."""

    rows = list(
        (
            await db.scalars(
                select(ForagerORM).where(ForagerORM.tenant_id == tenant_id),
            )
        ).all(),
    )
    resumed: list[str] = []
    for forager in rows:
        cfg = dict(forager.source_config or {})
        lane = str(cfg.get(FOUR_LANE_PAYLOAD_KEY) or "").strip().lower()
        name_match = any(
            hint.lower() in forager.name.lower()
            for hints in LANE_FORAGER_NAMES.values()
            for hint in hints
        )
        if lane not in FOUR_LANE_IDS and not name_match:
            continue
        if forager.supervisor_routine_id is None:
            continue
        routine = await db.get(SupervisorRoutine, forager.supervisor_routine_id)
        if routine is None:
            continue
        if not routine.is_active:
            routine.is_active = True
            resumed.append(routine.name)
        forager.is_active = True
    await db.flush()
    return resumed


def _is_queen_maintainer_routine(name: str) -> bool:
    return "queen maintainer" in _normalize_name(name)


def _is_forager_evaluator_routine(name: str) -> bool:
    normalized = _normalize_name(name)
    return normalized.startswith("forager ·") or normalized.startswith("forager -")


async def pause_legacy_routines(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Pause routines not tagged with four_lane_id (idempotent)."""

    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    paused: list[str] = []
    kept: list[str] = []
    for row in routines:
        lane = _lane_from_payload(dict(row.context_payload or {}))
        if lane in FOUR_LANE_IDS:
            kept.append(row.name)
            continue
        if _is_forager_evaluator_routine(row.name):
            kept.append(row.name)
            continue
        if row.is_active:
            row.is_active = False
            paused.append(row.name)
    await db.flush()
    logger.info(
        "solo_four_lanes.legacy_paused",
        agent_id="four_lane_bootstrap",
        swarm_id="",
        task_id=str(tenant_id),
        paused_count=len(paused),
    )
    return {"paused": paused, "kept": kept, "paused_count": len(paused)}


_DEFAULT_FORAGER_SCHEDULE: dict[str, Any] = {
    "enabled": True,
    "schedule_kind": "cron",
    "cron_expr": "0 6 * * 2,4",
    "runtime_mode": "durable",
}


async def _ensure_eshop_forager(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> ForagerORM | None:
    service = ForagerService(db=db)
    name = str(ESHOP_FORAGER_SPEC["name"])
    existing = await db.scalar(
        select(ForagerORM).where(
            ForagerORM.tenant_id == tenant_id,
            ForagerORM.name == name,
        ),
    )
    if existing is not None:
        payload = dict(existing.source_config or {})
        payload.update(dict(ESHOP_FORAGER_SPEC["source_config"]))
        payload[FOUR_LANE_PAYLOAD_KEY] = "eshop_research"
        existing.source_config = payload
        existing.is_active = True
        existing.description = str(ESHOP_FORAGER_SPEC["description"])
        await db.flush()
        return existing

    schedule = dict(_DEFAULT_FORAGER_SCHEDULE)
    schedule["cron_expr"] = str(ESHOP_FORAGER_SPEC["schedule_cron"])
    row = await service.create(
        tenant_id=tenant_id,
        name=name,
        description=str(ESHOP_FORAGER_SPEC["description"]),
        source_type=str(ESHOP_FORAGER_SPEC["source_type"]),
        source_config={
            **dict(ESHOP_FORAGER_SPEC["source_config"]),
            FOUR_LANE_PAYLOAD_KEY: "eshop_research",
        },
        filter_config={"default_tags": ["najman-eshop", "four-lane", "eshop-research"]},
        prompt_template=(
            "E-shop competitor RSS intel for beebrdy.cz. Summarize UX, pricing, product pages. "
            "Tag najman-eshop. Default simulate."
        ),
        tools=["hivemind", "retrieval"],
        is_active=bool(ESHOP_FORAGER_SPEC["is_active"]),
        agent_template_id=None,
        schedule=schedule,
        created_by_subject="four_lane_bootstrap",
    )
    await db.flush()
    return row


async def _lane_foragers_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lane_id: FourLaneId,
) -> list[FourLaneForagerOut]:
    """Read-only forager bindings for one lane."""

    names = LANE_FORAGER_NAMES[lane_id]
    rows = list(
        (
            await db.scalars(
                select(ForagerORM).where(ForagerORM.tenant_id == tenant_id),
            )
        ).all(),
    )
    out: list[FourLaneForagerOut] = []
    for hint in names:
        match = next((r for r in rows if hint.lower() in r.name.lower()), None)
        if match is None:
            out.append(FourLaneForagerOut(lane_id=lane_id, name=hint, is_active=False))
            continue
        out.append(
            FourLaneForagerOut(
                lane_id=lane_id,
                forager_id=str(match.id),
                name=match.name,
                is_active=bool(match.is_active),
                items_count=0,
            ),
        )
    return out


async def _configure_lane_foragers(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lane_id: FourLaneId,
) -> list[FourLaneForagerOut]:
    names = LANE_FORAGER_NAMES[lane_id]
    if lane_id == "eshop_research":
        await _ensure_eshop_forager(db, tenant_id=tenant_id)

    rows = list(
        (
            await db.scalars(
                select(ForagerORM).where(ForagerORM.tenant_id == tenant_id),
            )
        ).all(),
    )
    out: list[FourLaneForagerOut] = []
    for hint in names:
        match = next((r for r in rows if hint.lower() in r.name.lower()), None)
        if match is None:
            out.append(FourLaneForagerOut(lane_id=lane_id, name=hint, is_active=False))
            continue
        cfg = dict(match.source_config or {})
        cfg[FOUR_LANE_PAYLOAD_KEY] = lane_id
        match.source_config = cfg
        if lane_id == "tech_scv":
            match.is_active = True
        elif lane_id == "marketing_najman":
            match.is_active = True
        await db.flush()
        out.append(
            FourLaneForagerOut(
                lane_id=lane_id,
                forager_id=str(match.id),
                name=match.name,
                is_active=bool(match.is_active),
                items_count=0,
            ),
        )
    return out


async def compose_four_lane_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> FourLaneSnapshotOut:
    """Build operator snapshot for all four lanes."""

    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    legacy_paused = sum(
        1
        for row in routines
        if not row.is_active and _lane_from_payload(dict(row.context_payload or {})) not in FOUR_LANE_IDS
    )
    lanes: list[FourLaneOut] = []
    active_count = 0

    from app.application.services.solo_operator_digest_inbox import compose_four_lane_digest_inbox

    inbox = await compose_four_lane_digest_inbox(db, tenant_id=tenant_id, limit=40)
    pending_by_lane: dict[str, int] = {lid: 0 for lid in FOUR_LANE_IDS}
    promote_by_lane: dict[str, int] = {lid: 0 for lid in FOUR_LANE_IDS}
    first_promote: dict[str, str] = {}
    for item in inbox.items:
        lid = str(item.lane_id)
        if item.session_status in {"needs_input", "paused"} or (
            item.promote_ready and item.task_id is None
        ):
            pending_by_lane[lid] = pending_by_lane.get(lid, 0) + 1
        if item.promote_ready and item.task_id is None:
            promote_by_lane[lid] = promote_by_lane.get(lid, 0) + 1
            first_promote.setdefault(lid, item.session_id)

    for lane_id in FOUR_LANE_IDS:
        meta = LANE_META[lane_id]
        routine_row = next(
            (
                r
                for r in routines
                if _lane_from_payload(dict(r.context_payload or {})) == lane_id
                and not _is_queen_maintainer_routine(r.name)
            ),
            None,
        )
        if routine_row is None:
            routine_row = next(
                (
                    r
                    for r in routines
                    if _normalize_name(r.name) == _normalize_name(LANE_ROUTINE_NAMES[lane_id])
                ),
                None,
            )
        last_session: SupervisorSession | None = None
        if routine_row is not None and routine_row.is_active:
            active_count += 1
        if routine_row is not None:
            goal_hint = LANE_ROUTINE_NAMES[lane_id][:24]
            last_session = await db.scalar(
                select(SupervisorSession)
                .where(
                    SupervisorSession.tenant_id == tenant_id,
                    SupervisorSession.goal.ilike(f"%{goal_hint[:16]}%"),
                )
                .order_by(desc(SupervisorSession.created_at))
                .limit(1),
            )

        routine_out = FourLaneRoutineOut(
            lane_id=lane_id,
            routine_id=str(routine_row.id) if routine_row else None,
            routine_name=routine_row.name if routine_row else LANE_ROUTINE_NAMES[lane_id],
            is_active=bool(routine_row.is_active) if routine_row else False,
            schedule_cron=LANE_CRON[lane_id],
            last_session_id=str(last_session.id) if last_session else None,
            last_session_status=str(last_session.status) if last_session else None,
            last_run_at=last_session.created_at if last_session else None,
        )
        foragers = await _lane_foragers_snapshot(db, tenant_id=tenant_id, lane_id=lane_id)
        open_href = meta["open_href"]
        lanes.append(
            FourLaneOut(
                lane_id=lane_id,
                label=meta["label"],
                description=meta["description"],
                operator_hint=meta["operator_hint"],
                manual_anchor=meta["manual_anchor"],
                routine=routine_out,
                foragers=foragers,
                open_href=open_href,
                open_label=meta["open_label"],
                pending_digest_count=pending_by_lane.get(lane_id, 0),
                promote_ready_count=promote_by_lane.get(lane_id, 0),
                first_promote_session_id=first_promote.get(lane_id),
                approve_href=open_href,
                sessions_href=open_href,
            ),
        )

    return FourLaneSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        lanes=lanes,
        legacy_paused_count=legacy_paused,
        active_lane_count=active_count,
    )


async def ensure_four_lane_bootstrap(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str | None,
    pause_legacy: bool = True,
) -> dict[str, Any]:
    """Idempotent four-lane bootstrap: pause legacy, ensure routines + foragers."""

    maintainer = await ensure_queen_maintainer_routine(
        db,
        tenant_id=tenant_id,
        created_by_subject=created_by_subject,
        enabled=True,
    )
    maintainer_payload = dict(maintainer.context_payload or {})
    maintainer_payload[FOUR_LANE_PAYLOAD_KEY] = "tech_scv"
    maintainer_payload["four_lane_role"] = "maintainer"
    maintainer_payload["solo_operator_four_lane"] = True
    maintainer.context_payload = maintainer_payload
    maintainer.name = "Queen Maintainer — weekly tech health"

    pause_result: dict[str, Any] = {"paused_count": 0, "paused": []}
    if pause_legacy:
        pause_result = await pause_legacy_routines(db, tenant_id=tenant_id)

    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    lane_actions: list[dict[str, Any]] = []
    for lane_id in FOUR_LANE_IDS:
        row, action = await _ensure_lane_routine(
            db,
            tenant_id=tenant_id,
            lane_id=lane_id,
            routines=routines,
            created_by_subject=created_by_subject,
        )
        lane_actions.append(
            {
                "lane_id": lane_id,
                "action": action,
                "routine_id": str(row.id),
                "routine_name": row.name,
                "is_active": bool(row.is_active),
            },
        )
        routines = await _load_tenant_routines(db, tenant_id=tenant_id)

    for lane_id in FOUR_LANE_IDS:
        await _configure_lane_foragers(db, tenant_id=tenant_id, lane_id=lane_id)

    resumed_foragers = await _reactivate_lane_forager_routines(db, tenant_id=tenant_id)

    logger.info(
        "solo_four_lanes.bootstrap_complete",
        agent_id="four_lane_bootstrap",
        swarm_id="",
        task_id=str(tenant_id),
        lanes=len(lane_actions),
        legacy_paused=pause_result.get("paused_count", 0),
    )
    return {
        "ok": True,
        "lanes": lane_actions,
        "legacy": pause_result,
        "maintainer_routine_id": str(maintainer.id),
        "forager_routines_resumed": resumed_foragers,
    }


async def set_four_lane_active(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lane_id: FourLaneId,
    active: bool,
) -> dict[str, Any]:
    """Pause or resume one four-lane routine."""

    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    routine = next(
        (
            r
            for r in routines
            if _lane_from_payload(dict(r.context_payload or {})) == lane_id
            and not _is_queen_maintainer_routine(r.name)
        ),
        None,
    )
    if routine is None:
        return {"ok": False, "error": "lane_routine_not_found", "lane_id": lane_id}
    if lane_id == "automation" and active:
        active = True
    routine.is_active = active
    await db.flush()
    return {
        "ok": True,
        "lane_id": lane_id,
        "routine_id": str(routine.id),
        "is_active": bool(routine.is_active),
    }


async def trigger_automation_lane(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Manually run the automation factory routine (simulate-first checklist)."""

    from app.application.services.supervisor.routine_service import trigger_supervisor_routine_now
    from app.core.config import settings

    if not settings.routines_enabled:
        return {"ok": False, "error": "routines_disabled"}

    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    routine = next(
        (
            r
            for r in routines
            if _lane_from_payload(dict(r.context_payload or {})) == "automation"
            and not _is_queen_maintainer_routine(r.name)
        ),
        None,
    )
    if routine is None:
        return {"ok": False, "error": "lane_routine_not_found", "lane_id": "automation"}

    routine.is_active = True
    session_id = await trigger_supervisor_routine_now(db, routine=routine)
    await db.flush()
    logger.info(
        "solo_four_lanes.automation_triggered",
        agent_id="four_lane_automation",
        swarm_id="automation",
        task_id=str(session_id),
    )
    return {
        "ok": True,
        "lane_id": "automation",
        "routine_id": str(routine.id),
        "session_id": str(session_id),
        "sessions_href": f"/agents?session={session_id}#sessions",
        "tasks_href": "/tasks",
    }


__all__ = [
    "FOUR_LANE_IDS",
    "FourLaneId",
    "FourLaneOut",
    "FourLaneSnapshotOut",
    "compose_four_lane_snapshot",
    "ensure_four_lane_bootstrap",
    "pause_legacy_routines",
    "set_four_lane_active",
    "trigger_automation_lane",
]
