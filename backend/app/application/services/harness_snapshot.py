"""AI Layer harness snapshot — rules, skills, MCP tools, recent patterns."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.harness_tech_health import build_tech_health_report
from app.application.services.rubric_templates import list_rubric_templates
from app.core.repo_root import resolve_repo_root
from app.application.services.pattern_telemetry_service import build_pattern_telemetry
from app.application.services.supervisor.skills import SkillLibrary
from app.core.config import settings
from app.infrastructure.connectors.mcp_adapter import MCPAdapter
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession


def _collect_rule_layers(repo_root: Path) -> list[dict[str, str]]:
    """List layered harness rule files (root + .cursor/rules)."""

    layers: list[dict[str, str]] = []
    cursorrules = repo_root / ".cursorrules"
    if cursorrules.is_file():
        layers.append(
            {
                "id": "cursorrules",
                "path": ".cursorrules",
                "scope": "root",
                "bytes": str(cursorrules.stat().st_size),
            },
        )
    rules_dir = repo_root / ".cursor" / "rules"
    if rules_dir.is_dir():
        for item in sorted(rules_dir.glob("*.mdc")):
            if item.is_file():
                layers.append(
                    {
                        "id": item.stem,
                        "path": str(item.relative_to(repo_root)),
                        "scope": "module",
                        "bytes": str(item.stat().st_size),
                    },
                )
    agents_md = repo_root / "AGENTS.md"
    if agents_md.is_file():
        layers.append(
            {
                "id": "agents-md",
                "path": "AGENTS.md",
                "scope": "root",
                "bytes": str(agents_md.stat().st_size),
            },
        )
    for rel in ("backend/AGENTS.md", "frontend/AGENTS.md"):
        scoped = repo_root / rel
        if scoped.is_file():
            layers.append(
                {
                    "id": rel.replace("/", "-").replace(".", "-"),
                    "path": rel,
                    "scope": rel.split("/")[0],
                    "bytes": str(scoped.stat().st_size),
                },
            )
    return layers


def _collect_skills_summary() -> list[dict[str, Any]]:
    """Return compact skill catalog for harness dashboard."""

    lib = SkillLibrary()
    rows: list[dict[str, Any]] = []
    for slug in lib.list_available_slugs():
        skill = lib.load(slug)
        if skill is None:
            continue
        rows.append(
            {
                "slug": slug,
                "title": skill.title,
                "priority": skill.priority,
                "roles": list(skill.roles or []),
                "reference_mode": skill.reference_mode,
            },
        )
    rows.sort(key=lambda item: (-int(item["priority"]), str(item["slug"])))
    return rows


async def build_harness_snapshot(
    session: AsyncSession | None,
    *,
    tenant_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Build read-only AI Layer harness snapshot for Settings dashboard.

    Args:
        session: Optional DB session for MCP catalog + recent supervisor patterns.

    Returns:
        JSON-serializable harness overview.
    """
    repo_root = resolve_repo_root()
    skills = _collect_skills_summary()
    reference_mode_skills = sum(1 for row in skills if row.get("reference_mode"))
    mcp_tools: list[dict[str, Any]] = []
    if session is not None:
        mcp_tools = await MCPAdapter.dynamic_tool_catalog(session)

    recent_patterns: list[dict[str, Any]] = []
    if session is not None:
        stmt = (
            select(SupervisorSession)
            .where(SupervisorSession.context_summary.is_not(None))
            .order_by(desc(SupervisorSession.started_at))
            .limit(12)
        )
        sessions = list((await session.scalars(stmt)).all())
        for row in sessions:
            summary = dict(row.context_summary or {})
            patterns = summary.get("agentic_patterns")
            if not isinstance(patterns, dict):
                continue
            recent_patterns.append(
                {
                    "session_id": str(row.id),
                    "status": str(row.status or ""),
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "primary": list(patterns.get("primary") or []),
                    "secondary": list(patterns.get("secondary") or []),
                    "forced_reflection": bool(patterns.get("forced_reflection")),
                    "rationale": list(patterns.get("rationale") or [])[:4],
                },
            )
            if len(recent_patterns) >= 5:
                break

    tech_health = build_tech_health_report(repo_root=repo_root)

    slack_configured = bool((settings.slack_webhook_url or "").strip())
    monitoring: dict[str, Any] = {
        "slack_webhook_configured": slack_configured,
        "alertmanager_receiver": "slack-queenswarm" if slack_configured else "blackhole",
        "pattern_alert_rules": [
            "PatternSuccessRateLow",
            "PatternSuccessRateCritical",
            "PatternFailureBurst",
        ],
        "grafana_dashboard_uid": "queenswarm-agentic-patterns",
        "smoke_script": "scripts/alertmanager-smoke.sh",
    }
    if session is not None:
        monitoring["pattern_telemetry"] = await build_pattern_telemetry(
            session,
            tenant_id=tenant_id,
            window_hours=24,
            top_n=6,
        )

    return {
        "rule_layers": _collect_rule_layers(repo_root),
        "skills": {
            "count": len(skills),
            "reference_mode_count": reference_mode_skills,
            "items": skills[:24],
        },
        "mcp_tools": {
            "count": len(mcp_tools),
            "items": mcp_tools[:20],
        },
        "recent_agentic_patterns": recent_patterns,
        "feature_flags": {
            "supervisor_pattern_router_enabled": settings.supervisor_pattern_router_enabled,
            "supervisor_pattern_router_llm_enabled": settings.supervisor_pattern_router_llm_enabled,
            "supervisor_forced_reflection_enabled": settings.supervisor_forced_reflection_enabled,
            "supervisor_self_healing_enabled": settings.supervisor_self_healing_enabled,
            "queen_maintainer_enabled": settings.queen_maintainer_enabled,
            "routines_enabled": settings.routines_enabled,
            "skill_lazy_reference_fetch_enabled": settings.skill_lazy_reference_fetch_enabled,
            "tracer_bullet_kanban_enabled": settings.tracer_bullet_kanban_enabled,
            "tracer_bullet_kanban_auto_on_intake": settings.tracer_bullet_kanban_auto_on_intake,
            "slack_harness_trainer_enabled": settings.slack_harness_trainer_enabled,
            "lsp_mcp_bridge_enabled": settings.lsp_mcp_bridge_enabled,
            "rubric_templates_enabled": settings.rubric_templates_enabled,
        },
        "slack_trainer": {
            "enabled": settings.slack_harness_trainer_enabled,
            "signing_secret_configured": bool((settings.slack_harness_trainer_signing_secret or "").strip()),
            "tenant_id_configured": bool(
                settings.slack_harness_trainer_tenant_id and str(settings.slack_harness_trainer_tenant_id).strip(),
            ),
            "slash_command_path": "/api/v1/harness/slack-trainer/slack-command",
        },
        "lsp_bridge": {
            "enabled": settings.lsp_mcp_bridge_enabled,
            "connector_slug": "queenswarm_lsp",
            "tools": ["resolve_symbol", "list_file_symbols", "find_references"],
            "resolve_path": "/api/v1/harness/lsp-bridge/resolve",
        },
        "rubric_templates": {
            "enabled": settings.rubric_templates_enabled,
            "count": len(list_rubric_templates()),
            "list_path": "/api/v1/harness/rubric-templates",
        },
        "tech_health_score": tech_health.get("health_score"),
        "monitoring": monitoring,
        "docs": {
            "design_patterns": "docs/QUEENSWARM_DESIGN_PATTERNS.md",
            "harness_analysis": "docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md",
            "maintainer_instructions": "docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md",
        },
    }


__all__ = ["build_harness_snapshot"]
