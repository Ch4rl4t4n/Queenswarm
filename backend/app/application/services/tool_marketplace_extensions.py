"""Self-extending tool flow — goal-aware marketplace proposals with simulate-first gate."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.tool_marketplace import (
    _score_goal,
    _tokenize,
    install_marketplace_entry,
    marketplace_catalog,
)
from app.core.logging import get_logger
from app.infrastructure.connectors.phase3.catalog import get_phase3_template

logger = get_logger(__name__)

_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})


def _manager_matches(template_managers: list[str], manager_slug: str | None) -> bool:
    """Return True when template applies to the requested manager (or any if unset)."""

    target = (manager_slug or "").strip().lower()
    if not target:
        return True
    allowed = {m.strip().lower() for m in template_managers if str(m).strip()}
    if not allowed:
        return True
    return target in allowed


def simulate_phase3_template(entry_id: str) -> dict[str, Any]:
    """Validate a Phase 3 MCP template manifest without network I/O.

    Args:
        entry_id: Phase 3 template identifier.

    Returns:
        Simulation verdict with per-check details for operator review.
    """
    checks: list[dict[str, str]] = []
    try:
        template = get_phase3_template(entry_id)
    except KeyError:
        return {
            "entry_id": entry_id,
            "source": "phase3_template",
            "verified": False,
            "checks": [{"name": "template_exists", "status": "fail", "detail": "Unknown template id"}],
        }

    if not template.base_url.strip():
        checks.append({"name": "base_url", "status": "fail", "detail": "Missing base_url"})
    else:
        checks.append({"name": "base_url", "status": "pass", "detail": template.base_url[:120]})

    if not template.tools:
        checks.append({"name": "tools", "status": "fail", "detail": "No tools in manifest"})
    else:
        invalid = 0
        for tool in template.tools:
            name = str(tool.get("name") or "").strip()
            path = str(tool.get("path") or "").strip()
            method = str(tool.get("method") or "GET").upper()
            if not name or not path:
                invalid += 1
                continue
            if method not in _HTTP_METHODS:
                invalid += 1
        if invalid:
            checks.append(
                {
                    "name": "tools",
                    "status": "fail",
                    "detail": f"{invalid} tool row(s) missing name/path or invalid method",
                },
            )
        else:
            checks.append(
                {
                    "name": "tools",
                    "status": "pass",
                    "detail": f"{len(template.tools)} tool(s) structurally valid",
                },
            )

    auth = str(template.auth_type or "").strip().lower()
    known_auth = {"none", "api_key", "bearer", "bearer_token", "oauth2", "basic"}
    if auth not in known_auth:
        checks.append({"name": "auth_type", "status": "warn", "detail": f"Unusual auth_type: {auth}"})
    else:
        checks.append({"name": "auth_type", "status": "pass", "detail": auth})

    verified = all(c["status"] == "pass" for c in checks)
    return {
        "entry_id": entry_id,
        "source": "phase3_template",
        "slug": template.suggested_slug,
        "title": template.title,
        "verified": verified,
        "checks": checks,
    }


async def propose_marketplace_extensions(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    goal: str,
    manager_slug: str | None = None,
    limit: int = 6,
) -> dict[str, Any]:
    """Propose installable MCP presets for a task goal (read-only until simulate + install).

    Args:
        session: Async DB session.
        dashboard_user_id: Tenant dashboard user for catalog visibility.
        goal: Natural-language task goal for scoring.
        manager_slug: Optional manager filter.
        limit: Max proposals.

    Returns:
        Ranked proposals with optional pre-simulation verdict.
    """
    catalog = await marketplace_catalog(session, dashboard_user_id=dashboard_user_id)
    templates = catalog.get("phase3_templates")
    rows = [row for row in templates if isinstance(row, dict)] if isinstance(templates, list) else []
    goal_tokens = _tokenize(goal or "")
    cap = max(1, min(int(limit), 12))
    proposals: list[dict[str, Any]] = []

    for row in rows:
        if bool(row.get("installed")):
            continue
        entry_id = str(row.get("id") or "").strip()
        if not entry_id:
            continue
        managers = row.get("suggested_manager_slugs")
        mgr_list = [str(m) for m in managers] if isinstance(managers, list) else []
        if not _manager_matches(mgr_list, manager_slug):
            continue
        title = str(row.get("title") or entry_id)
        summary = str(row.get("summary") or "")
        score = _score_goal(goal_tokens, name=title, description=summary)
        if score <= 0.0 and goal_tokens:
            continue
        simulation = simulate_phase3_template(entry_id)
        proposals.append(
            {
                "source": "phase3_template",
                "entry_id": entry_id,
                "slug": str(row.get("slug") or ""),
                "title": title,
                "summary": summary,
                "score": float(f"{score:.4f}"),
                "tool_count": int(row.get("tool_count") or 0),
                "category": str(row.get("category") or ""),
                "simulation": simulation,
                "install_ready": bool(simulation.get("verified")),
            },
        )

    proposals.sort(key=lambda item: (-float(item.get("score") or 0.0), str(item.get("entry_id"))))
    trimmed = proposals[:cap]

    logger.info(
        "tool_marketplace_extensions.proposed",
        extra={
            "agent_id": "tool_marketplace",
            "swarm_id": "integrations",
            "task_id": str(dashboard_user_id),
            "proposal_count": len(trimmed),
        },
    )

    return {
        "goal": (goal or "").strip() or None,
        "manager_slug": (manager_slug or "").strip().lower() or None,
        "proposal_count": len(trimmed),
        "proposals": trimmed,
    }


async def install_verified_marketplace_extension(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    source: str,
    entry_id: str,
    require_simulation: bool = True,
) -> dict[str, Any]:
    """Install a marketplace entry only after manifest simulation passes.

    Args:
        session: Async DB session.
        dashboard_user_id: Installing user.
        source: Marketplace source (phase3_template).
        entry_id: Template id.
        require_simulation: When True, block install if simulation fails.

    Returns:
        Install status plus simulation payload.
    """
    src = source.strip().lower()
    simulation: dict[str, Any] | None = None
    if src == "phase3_template":
        simulation = simulate_phase3_template(entry_id)
        if require_simulation and not bool(simulation.get("verified")):
            return {
                "status": "simulation_failed",
                "simulation": simulation,
                "connector": None,
            }

    status, connector = await install_marketplace_entry(
        session,
        dashboard_user_id=dashboard_user_id,
        source=source,
        entry_id=entry_id,
    )
    payload: dict[str, Any] = {
        "status": status,
        "simulation": simulation,
    }
    if connector is not None:
        payload["connector"] = connector.model_dump(mode="json")
    return payload


__all__ = [
    "install_verified_marketplace_extension",
    "propose_marketplace_extensions",
    "simulate_phase3_template",
]
