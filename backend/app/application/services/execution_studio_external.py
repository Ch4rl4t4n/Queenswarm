"""External Execution Studio lane — auto-simulate on approved external proposals."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio import execute_studio_tool
from app.application.services.execution_studio_activity import persist_execution_activity
from app.core.logging import get_logger
from app.infrastructure.connectors.phase3.catalog import get_phase3_template, iter_phase3_templates
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)

_EXTERNAL_PROPOSAL_TYPE = "execution_studio_external"

_GOAL_CONNECTOR_HINTS: tuple[tuple[str, str], ...] = (
    ("slack", "slack_workspace"),
    ("notion", "notion_workspace"),
    ("github", "github_rest"),
    ("gitlab", "gitlab_rest"),
    ("stripe", "stripe_billing"),
    ("gmail", "gmail_workspace"),
    ("calendar", "google_calendar"),
    ("discord", "discord_guild"),
    ("telegram", "telegram_bot"),
)


def infer_connector_slug_from_goal(goal: str) -> str:
    """Pick a connector slug from goal keywords; default to notion_workspace."""

    lowered = goal.lower()
    for hint, slug in _GOAL_CONNECTOR_HINTS:
        if hint in lowered:
            return slug
    return "notion_workspace"


def infer_simulate_tool_name(connector_slug: str) -> str:
    """Return a read-safe tool name for simulate dry-run."""

    for template in iter_phase3_templates():
        if template.suggested_slug.strip().lower() != connector_slug.strip().lower():
            continue
        for tool in template.tools:
            if not isinstance(tool, dict):
                continue
            name = str(tool.get("name") or "").strip()
            method = str(tool.get("method") or "GET").upper()
            if name and method in {"GET", "HEAD"}:
                return name
        for tool in template.tools:
            if isinstance(tool, dict) and str(tool.get("name") or "").strip():
                return str(tool["name"]).strip()
    if connector_slug == "notion_workspace":
        return "search"
    return "list"


def _operator_id_from_subject(subject: str) -> uuid.UUID:
    if subject.startswith("dashboard:"):
        try:
            return uuid.UUID(subject.split(":", 1)[1])
        except ValueError:
            return uuid.uuid4()
    return uuid.uuid4()


async def execute_external_proposal_simulate(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    suggestion: AgentSuggestion,
    dashboard_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Run simulate-mode connector call for an approved external proposal."""

    payload = dict(suggestion.proposal_payload or {})
    if payload.get("simulate_executed_at"):
        return {"ok": True, "skipped": True, "reason": "already_simulated"}

    goal = str(payload.get("goal_excerpt") or suggestion.description or "").strip()
    connector_slug = str(payload.get("connector_slug") or infer_connector_slug_from_goal(goal))
    tool_name = str(payload.get("tool_name") or infer_simulate_tool_name(connector_slug))
    operator_id = dashboard_user_id or _operator_id_from_subject(str(suggestion.reviewed_by_subject or ""))

    result = await execute_studio_tool(
        session,
        dashboard_user_id=operator_id,
        tenant=tenant,
        connector_slug=connector_slug,
        tool_name=tool_name,
        arguments={"query": goal[:200]} if tool_name == "search" else {},
        mode="simulate",
    )

    live_result: dict[str, Any] | None = None
    live_pending: dict[str, Any] | None = None
    if result.get("ok"):
        live_result = await execute_studio_tool(
            session,
            dashboard_user_id=operator_id,
            tenant=tenant,
            connector_slug=connector_slug,
            tool_name=tool_name,
            arguments={"query": goal[:200]} if tool_name == "search" else {},
            mode="live",
        )
        live_pending = {
            "pending_approval": live_result.get("error") == "approval_required",
            "ok": live_result.get("ok"),
            "error": live_result.get("error"),
            "preview": live_result.get("preview"),
        }

    suggestion.proposal_payload = {
        **payload,
        "connector_slug": connector_slug,
        "tool_name": tool_name,
        "simulate_result": result,
        "simulate_executed_at": datetime.now(tz=UTC).isoformat(),
        "live_result": live_result,
        "live_pending_approval": bool(live_pending and live_pending.get("pending_approval")),
    }
    await session.flush()

    if tenant is not None:
        await persist_execution_activity(
            session,
            tenant,
            event_type="tool_execute",
            message=f"Auto-simulate external proposal: {connector_slug}/{tool_name}",
            payload={
                "proposal_id": str(suggestion.id),
                "connector_slug": connector_slug,
                "tool_name": tool_name,
                "mode": "simulate",
                "auto_approved": suggestion.reviewed_by_subject == "supervisor:auto",
            },
        )
        if live_pending is not None:
            await persist_execution_activity(
                session,
                tenant,
                event_type="tool_execute",
                message=(
                    f"External live pending approval: {connector_slug}/{tool_name}"
                    if live_pending.get("pending_approval")
                    else f"External auto-live: {connector_slug}/{tool_name}"
                ),
                payload={
                    "proposal_id": str(suggestion.id),
                    "connector_slug": connector_slug,
                    "tool_name": tool_name,
                    "mode": "live",
                    "pending_approval": live_pending.get("pending_approval"),
                },
            )
            if live_pending.get("pending_approval"):
                from app.application.services.execution_studio_notifications import notify_external_live_pending

                await notify_external_live_pending(
                    tenant=tenant,
                    proposal_id=suggestion.id,
                    connector_slug=connector_slug,
                    tool_name=tool_name,
                    goal_excerpt=goal,
                    session=session,
                )

    logger.info(
        "execution_studio.external_proposal_simulate",
        agent_id=suggestion.proposed_by_role,
        swarm_id=str(suggestion.tenant_id or ""),
        task_id=str(suggestion.id),
    )
    return {
        "ok": bool(result.get("ok")),
        "result": result,
        "connector_slug": connector_slug,
        "live_pending_approval": bool(live_pending and live_pending.get("pending_approval")),
    }


async def handoff_on_approved_external_proposal(
    session: AsyncSession,
    *,
    suggestion: AgentSuggestion,
    tenant: Tenant | None,
    reviewer_subject: str,
) -> dict[str, Any] | None:
    """Simulate connector execution when external proposal is approved."""

    if suggestion.proposal_type != _EXTERNAL_PROPOSAL_TYPE:
        return None
    if suggestion.status != "approved":
        return None
    if tenant is None:
        return {"ok": False, "error": "tenant_missing"}

    operator_id = _operator_id_from_subject(reviewer_subject)
    outcome = await execute_external_proposal_simulate(
        session,
        tenant=tenant,
        suggestion=suggestion,
        dashboard_user_id=operator_id,
    )
    return {
        "ok": outcome.get("ok", False),
        "lane": "external_simulate",
        "connector_slug": outcome.get("connector_slug"),
        "skipped": outcome.get("skipped"),
        "message": "External proposal simulate lane executed.",
    }


__all__ = [
    "execute_external_proposal_simulate",
    "handoff_on_approved_external_proposal",
    "infer_connector_slug_from_goal",
    "infer_simulate_tool_name",
]
