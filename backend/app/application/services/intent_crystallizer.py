"""Intent Crystallizer v2 — free text → goal plan, trust lane, deep links."""

from __future__ import annotations

import uuid
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = structlog.get_logger(__name__)

TrustLane = Literal["auto", "simulate", "live"]

_TEMPLATE_CATALOG: dict[str, dict[str, str]] = {
    "micro-saas-factory": {
        "label": "Micro-SaaS Factory",
        "href": "/factory",
        "swarm_href": "/swarms?template=micro-saas-factory",
    },
    "content-flywheel-v2": {
        "label": "Content Flywheel",
        "href": "/integrations?tab=studio#publish-queue",
        "swarm_href": "/swarms?template=content-flywheel-v2",
    },
    "polymarket-trading": {
        "label": "Polymarket Trading",
        "href": "/integrations?tab=studio#trading-cockpit",
        "swarm_href": "/swarms?template=polymarket-trading",
    },
    "exec-assistant": {
        "label": "Exec Assistant",
        "href": "/agents",
        "swarm_href": "/swarms?template=exec-assistant",
    },
}


class IntentCrystallizerStepOut(BaseModel):
    """One step in the crystallized workflow."""

    model_config = ConfigDict(extra="ignore")

    order: int
    label: str
    detail: str


class IntentCrystallizerPlanOut(BaseModel):
    """Crystallized intent plan with deep links."""

    model_config = ConfigDict(extra="ignore")

    title: str
    goal_description: str
    trust_lane: TrustLane
    suggested_templates: list[str] = Field(default_factory=list)
    template_labels: list[str] = Field(default_factory=list)
    steps: list[IntentCrystallizerStepOut] = Field(default_factory=list)
    deep_links: dict[str, str] = Field(default_factory=dict)
    primary_href: str = "/agents"
    summary_md: str = ""
    cockpit_href: str = "/cockpit#intent-crystallizer"


class IntentCrystallizerSnapshotOut(BaseModel):
    """Cockpit block for Intent Crystallizer."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    min_chars: int = 8
    trust_lanes: list[str] = Field(default_factory=lambda: ["auto", "simulate", "live"])
    templates: list[dict[str, str]] = Field(default_factory=list)


def compose_intent_crystallizer_snapshot() -> IntentCrystallizerSnapshotOut:
    """Static catalog for cockpit UI."""

    templates = [
        {"id": key, **meta}
        for key, meta in _TEMPLATE_CATALOG.items()
    ]
    return IntentCrystallizerSnapshotOut(
        enabled=settings.intent_crystallizer_enabled,
        templates=templates,
    )


def crystallize_intent(text: str) -> IntentCrystallizerPlanOut:
    """Heuristic intent → goal plan without LLM (fast, stable)."""

    stripped = text.strip()
    lowered = stripped.lower()
    templates: list[str] = []

    if any(k in lowered for k in ("factory", "saas", "landing", "mvp")):
        templates.append("micro-saas-factory")
    if any(k in lowered for k in ("publish", "tiktok", "instagram", "content", "marketing")):
        templates.append("content-flywheel-v2")
    if any(k in lowered for k in ("trade", "polymarket", "paper")):
        templates.append("polymarket-trading")
    if not templates:
        templates.append("exec-assistant")

    trust: TrustLane = "live" if any(k in lowered for k in ("live", "production", "deploy prod")) else "simulate"
    if any(k in lowered for k in ("research", "brief", "analyze", "scan")):
        trust = "auto"

    primary_template = templates[0]
    catalog = _TEMPLATE_CATALOG.get(primary_template, _TEMPLATE_CATALOG["exec-assistant"])
    labels = [_TEMPLATE_CATALOG.get(t, {}).get("label", t) for t in templates]

    steps = [
        IntentCrystallizerStepOut(
            order=1,
            label="Crystallize",
            detail="Intent parsed → swarm template + trust lane.",
        ),
        IntentCrystallizerStepOut(
            order=2,
            label="Queen goal",
            detail="Verify-first goal queued (simulate unless live confirm).",
        ),
        IntentCrystallizerStepOut(
            order=3,
            label="Critic gate",
            detail="Only APPROVED outputs reach operator.",
        ),
        IntentCrystallizerStepOut(
            order=4,
            label="Advanced UI",
            detail="Review in Agents / Factory / Swarms as needed.",
        ),
    ]

    deep_links = {
        "primary": catalog["href"],
        "swarm": catalog["swarm_href"],
        "cockpit": "/cockpit#intent-crystallizer",
        "agents": "/agents",
    }
    if "micro-saas-factory" in templates:
        deep_links["factory"] = "/factory"

    summary = (
        f"**{stripped[:120]}**\n"
        f"Templates: {', '.join(labels)}\n"
        f"Trust lane: `{trust}`"
    )

    return IntentCrystallizerPlanOut(
        title=stripped[:120],
        goal_description=stripped[:4000],
        trust_lane=trust,
        suggested_templates=templates,
        template_labels=labels,
        steps=steps,
        deep_links=deep_links,
        primary_href=catalog["href"],
        summary_md=summary,
    )


def format_crystallized_telegram(plan: IntentCrystallizerPlanOut, *, base_url: str) -> str:
    """Format crystallized plan for Telegram reply."""

    lines = [
        "💎 *Intent Crystallizer*",
        f"*{plan.title}*",
        f"Trust lane: `{plan.trust_lane}`",
        f"Templates: {', '.join(plan.template_labels)}",
        "",
        "*Steps:*",
    ]
    for step in plan.steps[:4]:
        lines.append(f"{step.order}. {step.label}")
    lines.append("")
    lines.append(f"{base_url.rstrip('/')}{plan.primary_href}")
    lines.append(f"{base_url.rstrip('/')}/cockpit#intent-crystallizer")
    return "\n".join(lines)


async def launch_crystallized_intent(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Any,
    reviewer_subject: str,
    plan: IntentCrystallizerPlanOut,
    spawn_factory: bool = False,
) -> dict[str, Any]:
    """Submit crystallized intent as Queen goal (verify-first)."""

    payload = plan.model_dump(mode="json")

    if spawn_factory or "micro-saas-factory" in plan.suggested_templates:
        from app.application.services.virtual_company_swarm_builder import build_department_swarm

        if tenant is not None:
            try:
                built = await build_department_swarm(
                    db,
                    tenant=tenant,
                    template_id="micro-saas-factory",
                    created_by_subject=reviewer_subject,
                    skip_if_exists=True,
                )
                payload["factory_swarm"] = built
            except KeyError:
                payload["factory_swarm"] = {"status": "template_missing"}

    if plan.trust_lane == "live":
        payload["requires_confirm"] = True
        return payload

    from app.application.services.goal_orchestrator import build_default_goal_orchestrator
    from app.worker.celery_app import celery_app

    orchestrator = build_default_goal_orchestrator()
    goal = await orchestrator.submit(
        tenant_id=tenant_id,
        user_id=dashboard_user_id,
        title=plan.title,
        description_md=plan.goal_description,
        acceptance_criteria_md="Simulate-first. Critic APPROVED before operator-facing output.",
        max_iterations=3,
        budget_usd=0.0,
    )
    celery_app.send_task("app.worker.tasks.goal_tasks.execute_goal", kwargs={"goal_id": str(goal.id)})
    payload["goal_id"] = str(goal.id)
    payload["href"] = f"/agents?goal={goal.id}"

    logger.info(
        "intent_crystallizer.launched",
        agent_id="intent_crystallizer",
        task_id=str(goal.id),
        trust_lane=plan.trust_lane,
    )
    return payload


__all__ = [
    "IntentCrystallizerPlanOut",
    "IntentCrystallizerSnapshotOut",
    "compose_intent_crystallizer_snapshot",
    "crystallize_intent",
    "format_crystallized_telegram",
    "launch_crystallized_intent",
]
