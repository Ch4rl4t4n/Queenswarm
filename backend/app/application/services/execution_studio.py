"""Execution Studio — product layer for external app connections and governed tool execution."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.application.services.queen_maintainer.pr_workflow import (
    MAINTAINER_DENYLIST_PREFIXES,
    build_branch_name,
    create_github_pr_if_configured,
    validate_changed_paths,
)
from app.application.services.queen_maintainer.service import (
    MAINTAINER_ROUTINE_NAME,
    MAINTAINER_ROLES,
    MAINTAINER_SKILLS,
    ensure_queen_maintainer_routine,
    queue_maintainer_run,
)
from app.application.services.queen_maintainer.maintainer_guard import (
    count_maintainer_runs_today,
    maintainer_budget_snapshot,
)
from app.application.services.queen_maintainer.tech_health import build_tech_health_report
from app.application.services.execution_studio_handoff import (
    count_pending_codebase_proposals,
    list_pending_codebase_proposals,
)
from app.application.services.execution_studio_activity import list_execution_activity, persist_execution_activity
from app.application.services.execution_studio_push import user_has_push_subscription
from app.application.services.execution_studio_telemetry import build_activity_telemetry
from app.application.services.execution_studio_notifications import (
    build_notification_test_status_ui,
    clear_notification_test_status,
    list_webhook_test_history,
)
from app.application.services.execution_studio_manual import build_execution_studio_manual
from app.application.services.supervisor.session_audit_digest_config import normalize_extra_recipients
from app.infrastructure.connectors.dynamic.credential_sync import hydrate_connector_secrets_from_vault
from app.infrastructure.connectors.dynamic.service import (
    DynamicConnectorService,
    _secrets_configured,
    invoke_dynamic_tool,
)
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.connectors.phase3.catalog import get_phase3_template, iter_phase3_templates
from app.infrastructure.connectors.phase3.marketplace_meta import marketplace_meta_for
from app.infrastructure.persistence.models.dynamic_connector import DynamicConnector
from app.infrastructure.persistence.models.tenant import Tenant

ExecutionMode = Literal["draft", "simulate", "live"]
RiskTier = Literal["read", "write", "publish", "financial"]

UNIVERSAL_SETUP_STEPS: tuple[dict[str, str], ...] = (
    {
        "id": "install",
        "title": "Install connection",
        "detail": "Pick a template in Tools Marketplace or create a custom HTTP bridge.",
    },
    {
        "id": "credentials",
        "title": "Connect credentials",
        "detail": "OAuth consent or API key via Connector Hub — secrets stay Fernet-sealed.",
    },
    {
        "id": "test",
        "title": "Test upstream",
        "detail": "Run connection test; successful probes activate the connector automatically.",
    },
    {
        "id": "assign",
        "title": "Assign to agents",
        "detail": "Allow manager lanes or Super Tool Routers so supervisor bees can invoke tools.",
    },
    {
        "id": "execute",
        "title": "Execute with policy",
        "detail": "Use draft / simulate / live modes. Live write actions respect approval settings.",
    },
)

CONNECTION_PACKS: tuple[dict[str, Any], ...] = (
    {
        "id": "productivity",
        "label": "Productivity",
        "description": "Notes, calendars, and workspace apps for research → deliverable flows.",
        "template_ids": ("notion_workspace", "google_calendar", "outlook_microsoft365"),
    },
    {
        "id": "communication",
        "label": "Communication",
        "description": "Mail and chat surfaces for notifications and operator handoffs.",
        "template_ids": ("gmail_google_workspace", "slack_web_api", "discord_bot_api", "telegram_bot_api"),
    },
    {
        "id": "social_publish",
        "label": "Social publish",
        "description": "Instagram, Facebook, X, and TikTok — post verified publish packs after operator approval.",
        "template_ids": (
            "instagram_graph_api",
            "facebook_graph_api",
            "twitter_api_v2",
            "tiktok_content_posting",
            "gmail_google_workspace",
            "resend_email_api",
        ),
    },
    {
        "id": "media",
        "label": "Media & generation",
        "description": "Image, copy, and creative tool routers for composed deliverables.",
        "template_ids": ("venice_mcp", "monid_mcp"),
    },
    {
        "id": "app_routers",
        "label": "App routers",
        "description": "OAuth hubs and action routers (Composio, Nango, Merge) for many SaaS apps.",
        "template_ids": ("composio_router", "nango_hub", "merge_agent_handler", "apify_store"),
    },
    {
        "id": "ecommerce",
        "label": "E-commerce",
        "description": "Shopify catalog/orders + Stripe Checkout — financial tier, simulate-first.",
        "template_ids": ("shopify_admin_api", "stripe_rest_api", "apify_store", "notion_workspace"),
    },
    {
        "id": "devtools",
        "label": "Devtools",
        "description": "Repos and automation for engineering execution lanes.",
        "template_ids": ("github_rest", "gitlab_rest"),
    },
    {
        "id": "codebase",
        "label": "Codebase & CI",
        "description": "Queen Maintainer PR-only lane — health sweeps, fixes, and dependency upgrades on our app.",
        "template_ids": ("github_rest", "gitlab_rest"),
        "lane": "internal",
    },
)

CODEBASE_SETUP_STEPS: tuple[dict[str, str], ...] = (
    {
        "id": "github_connector",
        "title": "Connect GitHub / GitLab",
        "detail": "Install github_rest or gitlab_rest from Marketplace, seal token, test to activate.",
    },
    {
        "id": "repo_target",
        "title": "Configure repo target",
        "detail": "Set QUEEN_MAINTAINER_GITHUB_OWNER and QUEEN_MAINTAINER_GITHUB_REPO in deployment env.",
    },
    {
        "id": "routine",
        "title": "Enable Maintainer routine",
        "detail": "Weekly supervisor routine (researcher + coder + critic) with queen-maintainer skill.",
    },
    {
        "id": "research_handoff",
        "title": "Research → proposal",
        "detail": "Research/optimization agents save proposals to HiveMind; operator approves via session review.",
    },
    {
        "id": "pr_only",
        "title": "PR-only execution",
        "detail": "Agents open branches queen-maintainer/* — denylist blocks secrets, billing, prod compose. You merge.",
    },
)

CODEBASE_REPO_SLUGS: frozenset[str] = frozenset({"github_rest", "gitlab_rest"})

MEDIA_TEMPLATE_IDS: tuple[str, ...] = ("venice_mcp", "monid_mcp")


def _studio_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get("execution_studio")
    return dict(bucket) if isinstance(bucket, dict) else {}


def studio_policy(tenant: Tenant | None) -> dict[str, Any]:
    """Return tenant execution policy with safe defaults."""

    bucket = _studio_bucket(tenant.operator_settings if tenant is not None else None)
    mode = _normalize_mode(str(bucket.get("default_mode") or "simulate"))
    return {
        "default_mode": mode,
        "live_requires_approval": bool(bucket.get("live_requires_approval", True)),
        "simulate_allows_read_calls": bool(bucket.get("simulate_allows_read_calls", True)),
        "codebase_default_mode": _normalize_mode(str(bucket.get("codebase_default_mode") or mode)),
        "live_codebase_requires_approval": bool(bucket.get("live_codebase_requires_approval", True)),
        "codebase_auto_approve_enabled": bool(bucket.get("codebase_auto_approve_enabled", False)),
        "codebase_pr_only": True,
    }


def _normalize_webhook_url(raw: object) -> str:
    """Normalize optional HTTPS webhook URL for operator notifications."""

    if not isinstance(raw, str):
        return ""
    cleaned = raw.strip()
    if not cleaned:
        return ""
    if not cleaned.startswith("https://"):
        return ""
    return cleaned


def _normalize_telegram_bot_token(raw: object) -> str:
    """Normalize Telegram bot token from BotFather."""

    if not isinstance(raw, str):
        return ""
    cleaned = raw.strip()
    if not cleaned or ":" not in cleaned:
        return ""
    bot_id, secret = cleaned.split(":", 1)
    if not bot_id.isdigit() or not secret.strip():
        return ""
    return cleaned


def _normalize_telegram_chat_id(raw: object) -> str:
    """Normalize Telegram chat id (user, group, or channel)."""

    if raw is None:
        return ""
    cleaned = str(raw).strip()
    return cleaned if cleaned else ""


def _normalize_teams_webhook_url(raw: object) -> str:
    """Normalize Teams / Power Automate webhook URL."""

    from app.presentation.api.routers.dashboard_session import teams_webhook_url_ok

    if not isinstance(raw, str):
        return ""
    cleaned = raw.strip()
    if not cleaned:
        return ""
    return cleaned if teams_webhook_url_ok(cleaned) else ""


def studio_notifications(tenant: Tenant | None) -> dict[str, Any]:
    """Return Execution Studio notification settings for operator UI."""

    bucket = _studio_bucket(tenant.operator_settings if tenant is not None else None)
    raw = bucket.get("notifications")
    notifications = dict(raw) if isinstance(raw, dict) else {}
    return {
        "email_recipients": normalize_extra_recipients(notifications.get("email_recipients")),
        "slack_webhook_url": _normalize_webhook_url(notifications.get("slack_webhook_url")),
        "discord_webhook_url": _normalize_webhook_url(notifications.get("discord_webhook_url")),
        "teams_webhook_url": _normalize_teams_webhook_url(notifications.get("teams_webhook_url")),
        "telegram_bot_token": _normalize_telegram_bot_token(notifications.get("telegram_bot_token")),
        "telegram_chat_id": _normalize_telegram_chat_id(notifications.get("telegram_chat_id")),
        "last_weekly_rollup_at": bucket.get("last_weekly_rollup_at"),
        "weekly_rollup_enabled": bool(get_settings().execution_studio_weekly_rollup_enabled),
        "webhook_test_status": build_notification_test_status_ui(tenant),
        "webhook_test_history": list_webhook_test_history(tenant, limit=10),
        "web_push_configured": bool(
            (get_settings().execution_studio_vapid_public_key or "").strip()
            and (get_settings().execution_studio_vapid_private_key or "").strip()
        ),
    }


def merge_studio_notifications_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial Execution Studio notifications patch."""

    root = dict(operator_settings or {})
    bucket = _studio_bucket(root)
    notifications = dict(bucket.get("notifications") or {}) if isinstance(bucket.get("notifications"), dict) else {}
    if "email_recipients" in patch:
        new_recipients = normalize_extra_recipients(patch.get("email_recipients"))
        old_recipients = normalize_extra_recipients(notifications.get("email_recipients"))
        notifications["email_recipients"] = new_recipients
        if new_recipients != old_recipients:
            clear_notification_test_status(notifications, "email")
    if "slack_webhook_url" in patch:
        new_url = _normalize_webhook_url(patch.get("slack_webhook_url"))
        old_url = _normalize_webhook_url(notifications.get("slack_webhook_url"))
        notifications["slack_webhook_url"] = new_url
        if new_url != old_url:
            clear_notification_test_status(notifications, "slack")
    if "discord_webhook_url" in patch:
        new_url = _normalize_webhook_url(patch.get("discord_webhook_url"))
        old_url = _normalize_webhook_url(notifications.get("discord_webhook_url"))
        notifications["discord_webhook_url"] = new_url
        if new_url != old_url:
            clear_notification_test_status(notifications, "discord")
    if "teams_webhook_url" in patch:
        new_url = _normalize_teams_webhook_url(patch.get("teams_webhook_url"))
        old_url = _normalize_teams_webhook_url(notifications.get("teams_webhook_url"))
        notifications["teams_webhook_url"] = new_url
        if new_url != old_url:
            clear_notification_test_status(notifications, "teams")
    if "telegram_bot_token" in patch:
        new_token = _normalize_telegram_bot_token(patch.get("telegram_bot_token"))
        old_token = _normalize_telegram_bot_token(notifications.get("telegram_bot_token"))
        notifications["telegram_bot_token"] = new_token
        if new_token != old_token:
            clear_notification_test_status(notifications, "telegram")
    if "telegram_chat_id" in patch:
        new_chat = _normalize_telegram_chat_id(patch.get("telegram_chat_id"))
        old_chat = _normalize_telegram_chat_id(notifications.get("telegram_chat_id"))
        notifications["telegram_chat_id"] = new_chat
        if new_chat != old_chat:
            clear_notification_test_status(notifications, "telegram")
    bucket["notifications"] = notifications
    root["execution_studio"] = bucket
    return root


def _normalize_mode(raw: str) -> ExecutionMode:
    cleaned = raw.strip().lower()
    if cleaned in {"draft", "simulate", "live"}:
        return cleaned  # type: ignore[return-value]
    return "simulate"


def merge_studio_policy_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial execution studio policy patch."""

    root = dict(operator_settings or {})
    bucket = _studio_bucket(root)
    if "default_mode" in patch:
        mode = str(patch["default_mode"]).strip().lower()
        if mode in {"draft", "simulate", "live"}:
            bucket["default_mode"] = mode
    if "live_requires_approval" in patch:
        bucket["live_requires_approval"] = bool(patch["live_requires_approval"])
    if "simulate_allows_read_calls" in patch:
        bucket["simulate_allows_read_calls"] = bool(patch["simulate_allows_read_calls"])
    if "codebase_default_mode" in patch:
        bucket["codebase_default_mode"] = _normalize_mode(str(patch["codebase_default_mode"]))
    if "live_codebase_requires_approval" in patch:
        bucket["live_codebase_requires_approval"] = bool(patch["live_codebase_requires_approval"])
    if "codebase_auto_approve_enabled" in patch:
        bucket["codebase_auto_approve_enabled"] = bool(patch["codebase_auto_approve_enabled"])
    root["execution_studio"] = bucket
    return root


def infer_risk_tier(
    *,
    connector_slug: str,
    method: str,
    tool_name: str,
    required_permission: str | None = None,
) -> RiskTier:
    """Heuristic risk classification for governed execution."""

    slug = connector_slug.strip().lower()
    meth = method.strip().upper()
    name = tool_name.strip().lower()
    perm = (required_permission or "").strip().lower()

    if "billing" in slug or "stripe" in slug or "shopify" in slug or perm == "tool:financial":
        return "financial"
    if any(token in name for token in ("publish", "post", "send", "create", "upload", "delete", "charge")):
        if meth in {"POST", "PUT", "PATCH", "DELETE"}:
            return "publish"
    if meth in {"POST", "PUT", "PATCH", "DELETE"} or perm in {"tool:write", "tool:execute"}:
        return "write"
    return "read"


def _connection_status(row: DynamicConnector, *, secrets_ok: bool) -> str:
    if row.is_active and secrets_ok:
        return "active"
    if not secrets_ok:
        return "needs_credentials"
    if secrets_ok and not row.is_active:
        return "ready_to_test"
    return "inactive"


def _template_id_for_slug(slug: str) -> str | None:
    cleaned = slug.strip().lower()
    for template in iter_phase3_templates():
        if template.suggested_slug == cleaned:
            return template.template_id
    return None


def build_media_tool_registry(*, connections: list[dict[str, Any]]) -> dict[str, Any]:
    """Return media/generation connector registry for Execution Studio UI."""

    by_slug = {str(row.get("slug") or "").lower(): row for row in connections}
    items: list[dict[str, Any]] = []
    for template_id in MEDIA_TEMPLATE_IDS:
        template = get_phase3_template(template_id)
        if template is None:
            continue
        meta = marketplace_meta_for(template_id)
        conn = by_slug.get(template.suggested_slug.lower())
        items.append(
            {
                "template_id": template_id,
                "slug": template.suggested_slug,
                "display_name": template.title,
                "status": str(conn.get("status") or "not_installed") if conn else "not_installed",
                "is_active": bool(conn.get("is_active")) if conn else False,
                "tools_count": int(conn.get("tools_count") or len(template.tools)) if conn else len(template.tools),
                "agent_usage": meta.get("agent_usage"),
                "cost_tier": meta.get("cost_tier") or "medium",
                "doc_url": meta.get("doc_url") or template.documentation_url,
            },
        )
    return {"pack_id": "media", "label": "Media & generation", "items": items}


def build_browser_fallback_lane() -> dict[str, Any]:
    """Browser harness fallback when connectors are unavailable."""

    settings = get_settings()
    return {
        "enabled": bool(settings.browser_harness_enabled),
        "role": "browser_operator",
        "lane": "fallback",
        "description": (
            "When OAuth connectors fail or no API exists, spawn browser_operator to verify "
            "surfaces via the headless harness (approval-gated writes)."
        ),
        "sessions_api": "/api/v1/agent-sessions/browser-harness/sessions",
        "execute_api": "/api/v1/execution-studio/browser/step",
        "supervisor_role": "browser_operator",
    }


def build_super_router_snapshot(tenant: Tenant | None) -> dict[str, Any]:
    """Expose tenant super tool routers for Execution Studio observability."""

    from app.application.services.super_tool_router import list_super_tool_routers

    routers = list_super_tool_routers(tenant)
    return {
        "count": len(routers),
        "active_count": sum(1 for row in routers if row.is_active),
        "items": [
            {
                "slug": row.slug,
                "name": row.name,
                "is_active": row.is_active,
                "routing_mode": row.routing_mode,
                "manager_slugs": list(row.manager_slugs),
                "connector_slugs": list(row.connector_slugs),
                "max_cost_tier": row.max_cost_tier,
            }
            for row in routers[:12]
        ],
    }


async def execution_studio_overview(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> dict[str, Any]:
    """Unified Execution Studio snapshot for the operator UI."""

    settings = get_settings()
    svc = DynamicConnectorService()
    rows = await svc.list_visible(session, dashboard_user_id=dashboard_user_id)
    owned_rows = tuple(
        (await session.scalars(select(DynamicConnector).where(DynamicConnector.dashboard_user_id == dashboard_user_id))).all()
    )
    slug_to_row: dict[str, DynamicConnector] = {row.slug.lower(): row for row in owned_rows}

    connections: list[dict[str, Any]] = []
    stats = {"active": 0, "needs_credentials": 0, "ready_to_test": 0, "inactive": 0}

    for public in rows:
        if public.is_builtin:
            continue
        orm = slug_to_row.get(public.slug.lower())
        if orm is None:
            continue
        secrets = svc._secrets_dict(orm)  # noqa: SLF001
        secrets_ok = _secrets_configured(orm.auth_type, secrets)
        status = _connection_status(orm, secrets_ok=secrets_ok)
        stats[status] = stats.get(status, 0) + 1

        manifest = dict(orm.mcp_manifest) if isinstance(orm.mcp_manifest, dict) else {}
        tools = manifest.get("tools") if isinstance(manifest.get("tools"), list) else []
        template_id = _template_id_for_slug(public.slug)
        meta = marketplace_meta_for(template_id) if template_id else {}

        connections.append(
            {
                "id": public.id,
                "slug": public.slug,
                "display_name": public.display_name,
                "auth_type": public.auth_type,
                "status": status,
                "is_active": bool(public.is_active),
                "tools_count": len(tools),
                "allowed_manager_slugs": list(public.allowed_manager_slugs or []),
                "template_id": template_id,
                "agent_usage": meta.get("agent_usage"),
                "doc_url": meta.get("doc_url"),
                "last_tested_at": public.last_tested_at,
            },
        )

    packs: list[dict[str, Any]] = []
    installed_slugs = {c["slug"] for c in connections}
    for pack in CONNECTION_PACKS:
        templates = []
        for tid in pack["template_ids"]:
            tpl = get_phase3_template(tid)
            if tpl is None:
                continue
            templates.append(
                {
                    "template_id": tid,
                    "slug": tpl.suggested_slug,
                    "display_name": tpl.title,
                    "installed": tpl.suggested_slug in installed_slugs,
                },
            )
        packs.append(
            {
                "id": pack["id"],
                "label": pack["label"],
                "description": pack["description"],
                "lane": pack.get("lane", "external"),
                "templates": templates,
            },
        )

    codebase = await build_codebase_lane_snapshot(
        session,
        tenant=tenant,
        connections=connections,
    )

    pending_proposals: list[dict[str, Any]] = []
    pending_proposals_total = 0
    if tenant is not None:
        pending_proposals_total = await count_pending_codebase_proposals(session, tenant_id=tenant.id)
        rows = await list_pending_codebase_proposals(session, tenant_id=tenant.id, limit=12)
        pending_proposals = [
            {
                "id": str(row.id),
                "title": row.title,
                "description": row.description[:500],
                "proposed_by_role": row.proposed_by_role,
                "risk_level": row.risk_level,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "goal_excerpt": str((row.proposal_payload or {}).get("goal_excerpt") or "")[:400],
            }
            for row in rows
        ]

    manual = build_execution_studio_manual()

    from app.application.services.execution_studio_pending import build_pending_approvals_snapshot

    pending_approvals = await build_pending_approvals_snapshot(session, tenant=tenant)

    notifications = studio_notifications(tenant)
    notifications["web_push_subscribed"] = user_has_push_subscription(tenant, user_id=dashboard_user_id)

    return {
        "enabled": bool(settings.execution_studio_enabled),
        "policy": studio_policy(tenant),
        "notifications": notifications,
        "stats": stats,
        "connections": sorted(connections, key=lambda row: row["display_name"].lower()),
        "packs": packs,
        "setup_steps": list(UNIVERSAL_SETUP_STEPS),
        "codebase": codebase,
        "manual": {
            "version": manual.get("version"),
            "title": manual.get("title"),
            "summary": manual.get("summary"),
            "section_count": len(manual.get("sections") or []),
            "flows": manual.get("flows"),
        },
        "pending_codebase_proposals": pending_proposals,
        "pending_codebase_proposals_total": pending_proposals_total,
        "pending_approvals": pending_approvals,
        "recent_activity": list_execution_activity(tenant, limit=20),
        "activity_telemetry": build_activity_telemetry(tenant, limit=40),
        "media_registry": build_media_tool_registry(connections=connections),
        "browser_fallback": build_browser_fallback_lane(),
        "super_routers": build_super_router_snapshot(tenant),
    }


def connection_setup_guide(*, template_id: str | None, slug: str) -> dict[str, Any]:
    """Return per-connection setup guidance for in-app manual."""

    meta = marketplace_meta_for(template_id) if template_id else {}
    template = get_phase3_template(template_id) if template_id else None
    auth_hint = template.auth_type if template is not None else "api_key"
    return {
        "slug": slug,
        "template_id": template_id,
        "display_name": template.display_name if template else slug,
        "auth_type": auth_hint,
        "agent_usage": meta.get("agent_usage"),
        "doc_url": meta.get("doc_url"),
        "setup_steps": list(UNIVERSAL_SETUP_STEPS),
        "recommended_managers": list(template.suggested_manager_slugs) if template else [],
    }


async def execute_studio_tool(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    connector_slug: str,
    tool_name: str,
    arguments: dict[str, Any],
    mode: ExecutionMode | None = None,
    manager_slug: str | None = None,
    operator_confirmed: bool = False,
    secrets_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Governed tool execution with draft / simulate / live modes."""

    settings = get_settings()
    if not settings.execution_studio_enabled:
        return {"ok": False, "error": "execution_studio_disabled"}

    policy = studio_policy(tenant)
    resolved_mode: ExecutionMode = mode or policy["default_mode"]  # type: ignore[assignment]

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=connector_slug.strip().lower())
    if row is None:
        return {"ok": False, "error": "connector_not_found"}

    await hydrate_connector_secrets_from_vault(session, row, dashboard_user_id=dashboard_user_id)

    manifest = dict(row.mcp_manifest) if isinstance(row.mcp_manifest, dict) else {"tools": []}
    tools_blob = manifest.get("tools") if isinstance(manifest.get("tools"), list) else []
    cfg_tool: dict[str, Any] | None = None
    for ent in tools_blob:
        if isinstance(ent, dict) and str(ent.get("name") or "").strip() == tool_name.strip():
            cfg_tool = ent
            break
    if cfg_tool is None:
        return {"ok": False, "error": "tool_not_found"}

    meth = str(cfg_tool.get("method") or "GET").upper()
    risk = infer_risk_tier(
        connector_slug=connector_slug,
        method=meth,
        tool_name=tool_name,
        required_permission=str(cfg_tool.get("required_permission") or "") or None,
    )

    preview = {
        "connector_slug": connector_slug,
        "tool_name": tool_name,
        "method": meth,
        "arguments": arguments,
        "risk_tier": risk,
    }

    if resolved_mode == "draft":
        result = {
            "ok": True,
            "mode": "draft",
            "executed": False,
            "risk_tier": risk,
            "preview": preview,
            "message": "Draft preview only — no upstream call was made.",
        }
        await persist_execution_activity(
            session,
            tenant,
            event_type="tool_execute",
            message=f"Draft preview: {connector_slug}/{tool_name}",
            payload={"mode": "draft", "risk_tier": risk, "executed": False},
        )
        return result

    if resolved_mode == "simulate":
        if risk != "read" or not policy["simulate_allows_read_calls"]:
            result = {
                "ok": True,
                "mode": "simulate",
                "executed": False,
                "risk_tier": risk,
                "preview": preview,
                "message": "Simulated success — write/publish tools stay dry-run until live mode.",
                "simulated_result": {"status": "simulated_ok", "echo": arguments},
            }
            await persist_execution_activity(
                session,
                tenant,
                event_type="tool_execute",
                message=f"Simulated: {connector_slug}/{tool_name}",
                payload={"mode": "simulate", "risk_tier": risk, "executed": False},
            )
            return result
        if not row.is_active:
            return {"ok": False, "error": "connector_inactive", "mode": "simulate", "risk_tier": risk}

    if resolved_mode == "live":
        if not row.is_active:
            return {"ok": False, "error": "connector_inactive", "mode": "live", "risk_tier": risk}
        if (
            policy["live_requires_approval"]
            and risk in {"write", "publish", "financial"}
            and not operator_confirmed
        ):
            from app.application.services.agentic_gates import evaluate_live_execution_gate

            gate = evaluate_live_execution_gate(
                mode=resolved_mode,
                risk_tier=risk,
                operator_confirmed=operator_confirmed,
                live_requires_approval=policy["live_requires_approval"],
                connector_slug=connector_slug,
            )
            if not gate.allowed:
                return {
                    "ok": False,
                    "error": gate.error_code or "approval_required",
                    "mode": "live",
                    "risk_tier": risk,
                    "preview": preview,
                    "message": gate.message or "Live write/publish/financial actions require operator approval.",
                    "gate": gate.gate.value,
                }

    if resolved_mode == "live" and operator_confirmed:
        from app.application.services.execution_studio_confirm_guard import (
            ExecutionStudioConfirmThrottledError,
            assert_operator_confirm_allowed,
        )

        try:
            await assert_operator_confirm_allowed(
                tenant_id=tenant.id if tenant is not None else None,
                lane=f"external:{connector_slug.strip().lower()}:{tool_name.strip()}",
            )
        except ExecutionStudioConfirmThrottledError as exc:
            return {
                "ok": False,
                "error": "confirm_throttled",
                "mode": "live",
                "risk_tier": risk,
                "retry_after_sec": exc.retry_after_sec,
                "message": "Please wait before confirming another live connector step.",
            }

    raw = await invoke_dynamic_tool(
        session,
        connector_slug=connector_slug,
        tool_name=tool_name,
        arguments=arguments,
        manager_slug=manager_slug,
        agent_task_id="execution-studio",
        secrets_override=secrets_override,
    )
    executed = not raw.startswith("dynamic_invoke_error:")
    result = {
        "ok": executed,
        "mode": resolved_mode,
        "executed": executed,
        "risk_tier": risk,
        "preview": preview,
        "result": raw if executed else None,
        "error": None if executed else raw,
    }
    await persist_execution_activity(
        session,
        tenant,
        event_type="tool_execute",
        message=f"{'Executed' if executed else 'Failed'}: {connector_slug}/{tool_name} ({resolved_mode})",
        payload={
            "mode": resolved_mode,
            "risk_tier": risk,
            "executed": executed,
            "connector_slug": connector_slug,
            "tool_name": tool_name,
        },
    )
    if resolved_mode == "live" and operator_confirmed and executed:
        from app.application.services.execution_studio_activity import persist_pending_live_cleared

        await persist_pending_live_cleared(
            session,
            tenant,
            lane="external",
            connector_slug=connector_slug,
            tool_name=tool_name,
        )
    return result


async def build_codebase_lane_snapshot(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    connections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Internal codebase execution lane — Queen Maintainer + repo connectors."""

    settings = get_settings()
    tech_health = build_tech_health_report()

    routine_enabled = False
    routine_id: str | None = None
    if tenant is not None:
        row = await session.scalar(
            select(SupervisorRoutine).where(
                SupervisorRoutine.tenant_id == tenant.id,
                SupervisorRoutine.name == MAINTAINER_ROUTINE_NAME,
            ),
        )
        if row is not None:
            routine_enabled = bool(row.is_active)
            routine_id = str(row.id)

    repo_connector = next(
        (
            conn
            for conn in connections
            if str(conn.get("slug") or "").lower() in CODEBASE_REPO_SLUGS
        ),
        None,
    )
    owner = settings.queen_maintainer_github_owner.strip()
    repo = settings.queen_maintainer_github_repo.strip()
    runs_today = 0
    if tenant is not None:
        runs_today = await count_maintainer_runs_today(session, tenant_id=tenant.id)

    return {
        "lane": "internal_codebase",
        "queen_maintainer_enabled": bool(settings.queen_maintainer_enabled),
        "budget": maintainer_budget_snapshot(runs_today=runs_today),
        "tech_health": {
            "health_score": tech_health.get("health_score"),
            "signals": list(tech_health.get("signals") or []),
            "backend_pinned_deps": (tech_health.get("backend") or {}).get("requirements_pinned_count", 0),
            "frontend_deps": (tech_health.get("frontend") or {}).get("dependency_count", 0),
        },
        "maintainer_routine": {
            "enabled": routine_enabled,
            "routine_id": routine_id,
        },
        "github_repo": {
            "owner": owner,
            "repo": repo,
            "configured": bool(owner and repo),
        },
        "repo_connector": repo_connector,
        "pr_only": True,
        "denylist_prefixes": list(MAINTAINER_DENYLIST_PREFIXES),
        "agent_roles": list(MAINTAINER_ROLES),
        "agent_skills": list(MAINTAINER_SKILLS),
        "setup_steps": list(CODEBASE_SETUP_STEPS),
    }


async def set_codebase_routine_enabled(
    session: AsyncSession,
    *,
    tenant: Tenant,
    created_by_subject: str,
    enabled: bool,
) -> dict[str, Any]:
    """Enable or pause Queen Maintainer weekly routine."""

    settings = get_settings()
    if not settings.queen_maintainer_enabled:
        return {"ok": False, "error": "queen_maintainer_disabled"}

    row = await ensure_queen_maintainer_routine(
        session,
        tenant_id=tenant.id,
        created_by_subject=created_by_subject,
        enabled=enabled,
    )
    return {
        "ok": True,
        "enabled": bool(row.is_active),
        "routine_id": str(row.id),
    }


async def trigger_codebase_maintainer_run(
    session: AsyncSession,
    *,
    tenant: Tenant,
    created_by_subject: str,
) -> dict[str, Any]:
    """Spawn Queen Maintainer supervisor session (research → code → PR draft)."""

    settings = get_settings()
    if not settings.queen_maintainer_enabled:
        return {"ok": False, "error": "queen_maintainer_disabled"}

    row = await ensure_queen_maintainer_routine(
        session,
        tenant_id=tenant.id,
        created_by_subject=created_by_subject,
        enabled=True,
    )
    result = await queue_maintainer_run(
        session,
        routine=row,
        trigger_source="execution_studio",
    )
    if not result.get("ok"):
        return result

    session_id = str(result["session_id"])
    await persist_execution_activity(
        session,
        tenant,
        event_type="maintainer_run",
        message="Queen Maintainer session queued from Execution Studio.",
        payload={"session_id": session_id, "routine_id": str(row.id)},
    )
    from app.application.services.queen_maintainer.maintainer_guard import maintainer_budget_snapshot

    return {
        "ok": True,
        "session_id": session_id,
        "routine_id": str(row.id),
        "message": "Queen Maintainer session queued — PR-only, denylist enforced, budget capped.",
        "budget": maintainer_budget_snapshot(runs_today=int(result.get("runs_today") or 0)),
    }


async def submit_codebase_pr_draft(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    title: str,
    body: str,
    slug: str,
    changed_paths: list[str],
    mode: ExecutionMode | None = None,
    operator_confirmed: bool = False,
) -> dict[str, Any]:
    """Governed codebase PR draft — draft/simulate preview or live PR via GitHub connector."""

    policy = studio_policy(tenant)
    resolved_mode: ExecutionMode = mode or policy["codebase_default_mode"]  # type: ignore[assignment]

    allowed, blocked = validate_changed_paths(changed_paths)
    if not allowed:
        return {"ok": False, "error": "denylist_blocked", "blocked_paths": blocked}

    branch = build_branch_name(slug=slug)
    preview = {
        "title": title,
        "branch": branch,
        "changed_paths": changed_paths,
        "pr_only": True,
    }

    if resolved_mode == "draft":
        result = {
            "ok": True,
            "mode": "draft",
            "executed": False,
            "preview": preview,
            "message": "PR draft preview — no GitHub call.",
        }
        await persist_execution_activity(
            session,
            tenant,
            event_type="pr_draft",
            message=f"PR draft preview: {slug}",
            payload={"mode": "draft", "slug": slug, "paths": changed_paths[:8]},
        )
        return result

    if resolved_mode == "simulate":
        result = {
            "ok": True,
            "mode": "simulate",
            "executed": False,
            "preview": preview,
            "message": "Simulated PR — paths passed denylist validation.",
        }
        await persist_execution_activity(
            session,
            tenant,
            event_type="pr_draft",
            message=f"Simulated PR: {slug}",
            payload={"mode": "simulate", "slug": slug, "paths": changed_paths[:8]},
        )
        return result

    if policy["live_codebase_requires_approval"] and not operator_confirmed:
        return {
            "ok": False,
            "error": "approval_required",
            "mode": "live",
            "preview": preview,
            "message": "Confirm live PR creation in Execution Studio (operator approval).",
        }

    result = await create_github_pr_if_configured(
        session,
        title=title,
        body=body,
        head_branch=branch,
    )
    created = str(result.get("status") or "") == "created"
    outcome = {
        "ok": created or str(result.get("status") or "") == "manual_required",
        "mode": "live",
        "executed": created,
        "preview": preview,
        "result": result,
        "error": None if created else str(result.get("reason") or result.get("status")),
    }
    await persist_execution_activity(
        session,
        tenant,
        event_type="pr_draft",
        message=f"Live PR {'created' if created else 'attempted'}: {slug}",
        payload={"mode": "live", "slug": slug, "executed": created},
    )
    return outcome


__all__ = [
    "CODEBASE_SETUP_STEPS",
    "CONNECTION_PACKS",
    "UNIVERSAL_SETUP_STEPS",
    "build_codebase_lane_snapshot",
    "connection_setup_guide",
    "execute_studio_tool",
    "execution_studio_overview",
    "infer_risk_tier",
    "merge_studio_notifications_patch",
    "merge_studio_policy_patch",
    "set_codebase_routine_enabled",
    "studio_notifications",
    "studio_policy",
    "submit_codebase_pr_draft",
    "trigger_codebase_maintainer_run",
]
