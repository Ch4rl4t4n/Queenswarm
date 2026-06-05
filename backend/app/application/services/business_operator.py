"""Chief Business Operator (CBO) — unified business snapshot for Cockpit (BA1)."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.marketing_product_catalog import build_catalog

if TYPE_CHECKING:
    from app.application.services.background_business_team import BackgroundBusinessTeamOut
    from app.application.services.business_goal_stack import BusinessGoalStackOut
from app.application.services.solo_daily_plan import compose_solo_daily_plan
from app.core.config import settings
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.tenant import Tenant

BusinessActionLane = Literal["revenue", "marketing", "factory", "ops", "trading", "po", "mission"]
BusinessActionPriority = Literal["high", "medium", "low"]

DEFAULT_EXPORT_ROOTS: tuple[Path, ...] = (
    Path("exports"),
    Path(__file__).resolve().parents[4] / "exports",
    Path("/exports"),
    Path("/app/exports"),
)


class BusinessOperatorActionOut(BaseModel):
    """One prioritized business action."""

    model_config = ConfigDict(extra="ignore")

    id: str
    lane: BusinessActionLane
    title: str
    detail: str
    priority: BusinessActionPriority
    href: str | None = None


class BusinessCatalogSummaryOut(BaseModel):
    """Marketing catalog rollup."""

    model_config = ConfigDict(extra="ignore")

    product_count: int = 0
    featured_count: int = 0
    gumroad_linked_count: int = 0
    marketing_origin: str = "https://letagentscook.org"


class BusinessRevenueSummaryOut(BaseModel):
    """Gumroad / scorecard revenue loop."""

    model_config = ConfigDict(extra="ignore")

    ready_summary: str = "unknown"
    scorecard_ready_count: int | None = None
    first_upload_candidate: str | None = None
    next_operator_action: str = ""
    missing_reports: list[str] = Field(default_factory=list)


class BusinessMissionSummaryOut(BaseModel):
    """Mission kanban pressure."""

    model_config = ConfigDict(extra="ignore")

    triage_count: int = 0
    ready_count: int = 0
    in_progress_count: int = 0
    blocked_count: int = 0


class BusinessOperatorSnapshotOut(BaseModel):
    """Read-only CBO brief."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    headline: str = ""
    tagline: str = "Internal harness brief — simulate-first, free-first LLM, operator approves live actions."
    catalog: BusinessCatalogSummaryOut = Field(default_factory=BusinessCatalogSummaryOut)
    revenue: BusinessRevenueSummaryOut = Field(default_factory=BusinessRevenueSummaryOut)
    missions: BusinessMissionSummaryOut = Field(default_factory=BusinessMissionSummaryOut)
    top_actions: list[BusinessOperatorActionOut] = Field(default_factory=list)
    goal_stack: BusinessGoalStackOut | None = None
    background_team: BackgroundBusinessTeamOut | None = None
    links: dict[str, str] = Field(default_factory=dict)


def _resolve_export_root(export_root: Path | None = None) -> Path:
    if export_root is not None:
        return export_root.expanduser().resolve()
    for candidate in DEFAULT_EXPORT_ROOTS:
        resolved = candidate.expanduser().resolve()
        if (resolved / "gumroad-ready").is_dir():
            return resolved
    return Path("exports").resolve()


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _first_match(text: str, pattern: str, default: str = "") -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else default


def _count_gumroad_uploads(export_root: Path) -> int:
    state_path = export_root / "gumroad-upload-status.json"
    if not state_path.is_file():
        return 0
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    products = payload.get("products")
    if not isinstance(products, dict):
        return 0
    return sum(
        1
        for row in products.values()
        if isinstance(row, dict) and str(row.get("gumroad_url") or row.get("url") or "").strip()
    )


def compose_revenue_summary(export_root: Path | None = None) -> BusinessRevenueSummaryOut:
    """Parse operator export reports into structured revenue summary."""

    root = _resolve_export_root(export_root)
    paths = {
        "upload_queue": root / "gumroad-ready" / "UPLOAD_QUEUE.md",
        "scorecard": root / "GUMROAD_SCORECARD.md",
        "business_simulation": root / "business-simulations" / "GUMROAD_LAUNCH_STRATEGY.md",
        "objective_audit": root / "guardrail-audits" / "GUMROAD_OBJECTIVE_AUDIT.md",
        "model_eval": root / "model-evals" / "MODEL_EVAL_REPORT.md",
        "token_readiness": root / "OPERATOR_TOKEN_READINESS.md",
    }
    bodies = {key: _read_text(path) for key, path in paths.items()}
    missing = [key for key, body in bodies.items() if not body]

    ready_summary = _first_match(bodies["scorecard"], r"^(Ready:\s+\*\*[^*]+\*\*)$", default="unknown")
    count_match = re.search(r"Ready:\s+\*\*(\d+)/(\d+)\*\*", bodies["scorecard"])
    ready_count = int(count_match.group(1)) if count_match else None
    first_product = _first_match(bodies["upload_queue"], r"^1\.\s+(`[^`]+`.*)$") or None

    uploaded = _count_gumroad_uploads(root)
    catalog_count = build_catalog(root).product_count
    if missing:
        next_action = "Regenerate operator reports before Gumroad upload."
    elif uploaded == 0 and first_product:
        next_action = f"Upload first listing manually: {first_product}"
    elif uploaded < catalog_count:
        next_action = f"Continue Gumroad upload ({uploaded}/{catalog_count} linked)."
    else:
        next_action = "Drive traffic to letagentscook.org and track first sale."

    return BusinessRevenueSummaryOut(
        ready_summary=ready_summary,
        scorecard_ready_count=ready_count,
        first_upload_candidate=first_product,
        next_operator_action=next_action,
        missing_reports=missing,
    )


async def _mission_counts(db: AsyncSession, *, tenant_id: uuid.UUID) -> BusinessMissionSummaryOut:
    async def _count(status: TaskStatus) -> int:
        value = await db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.tenant_id == tenant_id,
                Task.status == status,
                Task.payload.contains({"mission_kanban": True}),
            ),
        )
        return int(value or 0)

    triage, ready, blocked, in_progress = await asyncio.gather(
        _count(TaskStatus.TRIAGE),
        _count(TaskStatus.READY),
        _count(TaskStatus.BLOCKED),
        _count(TaskStatus.RUNNING),
    )
    return BusinessMissionSummaryOut(
        triage_count=triage,
        ready_count=ready,
        blocked_count=blocked,
        in_progress_count=in_progress,
    )


def _priority_label(rank: int) -> BusinessActionPriority:
    if rank <= 1:
        return "high"
    if rank == 2:
        return "medium"
    return "low"


def _derive_top_actions(
    *,
    revenue: BusinessRevenueSummaryOut,
    catalog: BusinessCatalogSummaryOut,
    missions: BusinessMissionSummaryOut,
    daily_items: list[dict[str, object]],
    goal_stack: BusinessGoalStackOut | None = None,
) -> list[BusinessOperatorActionOut]:
    candidates: list[tuple[int, BusinessOperatorActionOut]] = []

    if goal_stack is not None:
        lane_from_goal: dict[str, BusinessActionLane] = {
            "revenue": "revenue",
            "marketing": "marketing",
            "factory": "factory",
            "mission": "mission",
            "trading": "trading",
            "ops": "ops",
        }
        for goal in goal_stack.goals:
            if goal.drift_severity == "critical":
                lane_key = goal.mission_lane or "ops"
                candidates.append(
                    (
                        1,
                        BusinessOperatorActionOut(
                            id=f"goal_drift_{goal.id}",
                            lane=lane_from_goal.get(lane_key, "ops"),
                            title=f"Goal drift: {goal.label}",
                            detail=goal.drift_detail,
                            priority="high",
                            href="/cockpit#business-operator",
                        ),
                    ),
                )

    if revenue.missing_reports:
        candidates.append(
            (
                1,
                BusinessOperatorActionOut(
                    id="regenerate_reports",
                    lane="revenue",
                    title="Regenerate revenue reports",
                    detail=f"Missing: {', '.join(revenue.missing_reports[:4])}",
                    priority="high",
                    href="/factory",
                ),
            ),
        )
    elif catalog.gumroad_linked_count == 0 and revenue.first_upload_candidate:
        candidates.append(
            (
                1,
                BusinessOperatorActionOut(
                    id="gumroad_first_upload",
                    lane="revenue",
                    title="First Gumroad upload",
                    detail=revenue.next_operator_action,
                    priority="high",
                    href="/factory",
                ),
            ),
        )
    elif catalog.gumroad_linked_count < catalog.product_count:
        gap = catalog.product_count - catalog.gumroad_linked_count
        candidates.append(
            (
                1,
                BusinessOperatorActionOut(
                    id="gumroad_continue_upload",
                    lane="revenue",
                    title="Continue Gumroad catalog upload",
                    detail=f"{gap} listing(s) without Gumroad URL — {revenue.next_operator_action}",
                    priority="high",
                    href="/factory",
                ),
            ),
        )

    if missions.triage_count > 0:
        candidates.append(
            (
                1 if missions.triage_count >= 2 else 2,
                BusinessOperatorActionOut(
                    id="mission_triage",
                    lane="mission",
                    title=f"Review {missions.triage_count} triage mission(s)",
                    detail="Dispatch or clear Mission Control before starting new work.",
                    priority=_priority_label(1 if missions.triage_count >= 2 else 2),
                    href="/tasks",
                ),
            ),
        )

    lane_map: dict[str, BusinessActionLane] = {
        "po": "po",
        "marketing": "marketing",
        "trading": "trading",
        "ops": "ops",
    }
    for item in daily_items[:3]:
        lane_raw = str(item.get("lane") or "ops")
        lane = lane_map.get(lane_raw, "ops")
        rank = min(3, max(1, int(item.get("priority") or 3)))
        candidates.append(
            (
                rank,
                BusinessOperatorActionOut(
                    id=str(item.get("id") or "daily"),
                    lane=lane,
                    title=str(item.get("title") or "Daily action"),
                    detail=str(item.get("detail") or ""),
                    priority=_priority_label(rank),
                    href=str(item.get("href") or "") or None,
                ),
            ),
        )

    if catalog.product_count > 0:
        candidates.append(
            (
                2,
                BusinessOperatorActionOut(
                    id="promote_catalog",
                    lane="marketing",
                    title=f"Promote {catalog.product_count} live listings",
                    detail="Share letagentscook.org/skills after Gumroad products are live.",
                    priority="medium",
                    href="https://letagentscook.org/skills",
                ),
            ),
        )

    candidates.sort(key=lambda row: row[0])
    seen: set[str] = set()
    actions: list[BusinessOperatorActionOut] = []
    for _, action in candidates:
        if action.id in seen:
            continue
        seen.add(action.id)
        actions.append(action)
    if not actions:
        actions.append(
            BusinessOperatorActionOut(
                id="open_agents",
                lane="ops",
                title="Start a supervisor session",
                detail="No urgent blockers — pick a goal in Agents → Sessions.",
                priority="medium",
                href="/agents#sessions",
            ),
        )
    return actions[:3]


def _headline(actions: list[BusinessOperatorActionOut], missions: BusinessMissionSummaryOut) -> str:
    if actions:
        return actions[0].title
    if missions.triage_count > 0:
        return f"{missions.triage_count} mission(s) in triage"
    return "Business loop ready"


async def compose_business_operator_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    export_root: Path | None = None,
) -> BusinessOperatorSnapshotOut:
    """Assemble read-only CBO brief from verified subsystems."""

    if not settings.operator_control_plane_enabled:
        return BusinessOperatorSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    from app.application.services.background_business_team import compose_background_business_team
    from app.application.services.business_goal_stack import compose_business_goal_stack

    catalog_payload = build_catalog(export_root)
    gumroad_linked = sum(1 for product in catalog_payload.products if product.gumroad_url)
    catalog = BusinessCatalogSummaryOut(
        product_count=catalog_payload.product_count,
        featured_count=sum(1 for product in catalog_payload.products if product.featured),
        gumroad_linked_count=max(gumroad_linked, _count_gumroad_uploads(_resolve_export_root(export_root))),
    )
    revenue = compose_revenue_summary(export_root)
    factory_queue_count = 0
    trading_paper_mode = True
    if settings.skill_factory_enabled:
        try:
            from app.application.services.skill_factory_service import compose_skill_factory_snapshot

            factory_snap = await compose_skill_factory_snapshot(db, tenant_id=tenant_id)
            factory_queue_count = int(factory_snap.queue_count or 0) + int(factory_snap.building_count or 0)
        except Exception:
            factory_queue_count = 0
    try:
        from app.application.services.trading_cockpit import compose_trading_cockpit_snapshot

        trading_snap = await compose_trading_cockpit_snapshot(
            db,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
        )
        trading_paper_mode = str((trading_snap.config or {}).get("default_mode") or "paper") == "paper"
    except Exception:
        trading_paper_mode = True

    missions = await _mission_counts(db, tenant_id=tenant_id)
    daily, goal_stack, background_team = await asyncio.gather(
        compose_solo_daily_plan(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            max_items=5,
        ),
        compose_business_goal_stack(
            db,
            tenant_id=tenant_id,
            tenant=tenant,
            catalog=catalog,
            missions=missions,
            revenue=revenue,
            factory_queue_count=factory_queue_count,
            trading_paper_mode=trading_paper_mode,
        ),
        compose_background_business_team(db, tenant_id=tenant_id, tenant=tenant),
    )
    daily_items = [item.model_dump(mode="json") for item in daily.items]
    top_actions = _derive_top_actions(
        revenue=revenue,
        catalog=catalog,
        missions=missions,
        daily_items=daily_items,
        goal_stack=goal_stack,
    )

    return BusinessOperatorSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        headline=_headline(top_actions, missions),
        catalog=catalog,
        revenue=revenue,
        missions=missions,
        top_actions=top_actions,
        goal_stack=goal_stack,
        background_team=background_team,
        links={
            "agents_sessions": "/agents#sessions",
            "mission_control": "/tasks",
            "factory": "/factory",
            "marketing_skills": "https://letagentscook.org/skills",
        },
    )


async def fetch_business_mission_summary(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> BusinessMissionSummaryOut:
    """Public wrapper for mission kanban counts used by BA2 API."""

    return await _mission_counts(db, tenant_id=tenant_id)


def _rebuild_business_operator_models() -> None:
    """Resolve forward refs for nested BA2/BA3 snapshot models."""

    from app.application.services.background_business_team import BackgroundBusinessTeamOut
    from app.application.services.business_goal_stack import BusinessGoalStackOut

    BusinessOperatorSnapshotOut.model_rebuild(
        _types_namespace={
            "BackgroundBusinessTeamOut": BackgroundBusinessTeamOut,
            "BusinessGoalStackOut": BusinessGoalStackOut,
        },
    )


_rebuild_business_operator_models()


__all__ = [
    "BusinessMissionSummaryOut",
    "BusinessOperatorSnapshotOut",
    "compose_business_operator_snapshot",
    "compose_revenue_summary",
    "fetch_business_mission_summary",
]
