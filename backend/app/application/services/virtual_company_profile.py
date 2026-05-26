"""Virtual Company operator profile and bootstrap checklist (solo free-first)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.llm_routing import load_routing_config, merge_routing_patch, normalize_routing_mode
from app.application.services.tool_marketplace import install_marketplace_entry
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.tenant import Tenant

VIRTUAL_COMPANY_PROFILE_BUCKET = "virtual_company_profile"

RiskTolerance = Literal["low", "medium", "high"]

DEFAULT_FOCUS_AREAS: tuple[str, ...] = (
    "marketing",
    "sales",
    "product",
    "technology",
)

DEPARTMENT_CONNECTOR_MAP: dict[str, tuple[str, ...]] = {
    "marketing": ("notion_workspace", "gmail_workspace"),
    "sales": ("gmail_workspace", "notion_workspace"),
    "finance": ("notion_workspace",),
    "digital": ("notion_workspace",),
    "rnd": ("github_rest", "notion_workspace"),
    "product": ("github_rest", "notion_workspace"),
}

ALL_SUGGESTED_CONNECTORS: frozenset[str] = frozenset(
    slug for slugs in DEPARTMENT_CONNECTOR_MAP.values() for slug in slugs
)

# Phase 3 template_id per connector slug (suggested_slug may differ for Gmail).
FREE_CONNECTOR_INSTALLS: tuple[tuple[str, str], ...] = (
    ("notion_workspace", "notion_workspace"),
    ("gmail_workspace", "gmail_google_workspace"),
    ("github_rest", "github_rest"),
)

OAUTH_PROVIDER_BY_CONNECTOR_SLUG: dict[str, str] = {
    "notion_workspace": "notion_workspace",
    "gmail_workspace": "google_gmail",
    "github_rest": "github_rest",
    "instagram_graph": "instagram_graph",
    "facebook_graph": "facebook_graph",
    "twitter_api_v2": "twitter_api_v2",
    "tiktok_content": "tiktok_content",
}

DEFAULT_SOLO_PROFILE_PATCH: dict[str, Any] = {
    "brand_name": "Queenswarm Solo",
    "industry": "Virtual Company / AI Operations",
    "focus_areas": list(DEFAULT_FOCUS_AREAS),
    "risk_tolerance": "medium",
    "primary_goal": (
        "Run department swarms in simulate mode with free-first LLM routing and verified Execution Studio outputs."
    ),
}

SOLO_SUPER_ROUTER_PROVISION: tuple[dict[str, str], ...] = (
    {
        "preset_id": "solo_app_actions",
        "slug": "vc_solo_app_actions",
        "name": "VC Solo App Actions",
    },
    {
        "preset_id": "solo_dev_workspace",
        "slug": "vc_solo_dev_workspace",
        "name": "VC Solo Dev Workspace",
    },
)

# Minimum active connectors before auto-activating a solo router (partial VC paths).
SOLO_ROUTER_PARTIAL_MIN_CONNECTORS: dict[str, frozenset[str]] = {
    "vc_solo_app_actions": frozenset({"notion_workspace"}),
    "vc_solo_dev_workspace": frozenset({"github_rest"}),
}

FIRST_RUN_PLAYBOOKS: dict[str, dict[str, Any]] = {
    "marketing-ops": {
        "title": "Marketing Ops · first simulate run",
        "goal": (
            "Run Marketing Ops in simulate mode: research 3 topics from HiveMind, draft 1 long-form post, "
            "stage a Notion page via mcp_invoke (simulate only), prepare a Gmail draft — no live writes."
        ),
        "runtime_mode": "durable",
        "skills": ["execution-studio", "context", "decide"],
        "roles": ["researcher", "coder", "critic"],
    },
    "lead-waterfall": {
        "title": "Sales Ops · first simulate run",
        "goal": (
            "Run Sales Ops in simulate mode: qualify 5 leads in Notion, draft outreach emails in Gmail simulate mode — "
            "operator approval before any live send."
        ),
        "runtime_mode": "durable",
        "skills": ["execution-studio", "context", "decide"],
        "roles": ["researcher", "coder", "critic"],
    },
    "rnd-dev": {
        "title": "R&D · first simulate run",
        "goal": (
            "Run R&D in simulate mode: summarize open GitHub issues, draft a fix plan in Notion simulate mode — "
            "no live PR without approval."
        ),
        "runtime_mode": "durable",
        "skills": ["execution-studio", "context", "decide"],
        "roles": ["researcher", "coder", "critic"],
    },
    "finance-ops": {
        "title": "Finance Ops · first simulate run",
        "goal": (
            "Run Finance Ops in simulate mode: weekly cashflow snapshot from HiveMind, budget variance notes, "
            "anomaly flags — write report page to Notion simulate mode only, no banking API calls."
        ),
        "runtime_mode": "durable",
        "skills": ["execution-studio", "context", "decide"],
        "roles": ["researcher", "coder", "critic"],
    },
    "digital-ops": {
        "title": "Digital Ops · first simulate run",
        "goal": (
            "Run Digital Ops in simulate mode: 3 UX findings, 2 conversion hypotheses, experiment backlog "
            "updated in Notion simulate mode — no paid analytics APIs."
        ),
        "runtime_mode": "durable",
        "skills": ["execution-studio", "context", "decide"],
        "roles": ["researcher", "coder", "critic"],
    },
    "product-ship": {
        "title": "Product Ship · first simulate run",
        "goal": (
            "Run Product Ship in simulate mode: PRD slice review, blocked items list, Notion roadmap update "
            "simulate mode — next vertical slice queued for operator approval, no live GitHub writes."
        ),
        "runtime_mode": "durable",
        "skills": ["execution-studio", "context", "decide"],
        "roles": ["researcher", "coder", "critic"],
    },
    "life-os": {
        "title": "Life OS · first simulate run",
        "goal": (
            "Run Life OS in simulate mode: process overnight dump ingest, extract 5 prioritized tasks, "
            "compile verified morning briefing from HiveMind — no live writes, simulate only."
        ),
        "runtime_mode": "durable",
        "skills": ["execution-studio", "context", "automation-proposal"],
        "roles": ["researcher", "coder", "critic"],
    },
}

VC_DEPARTMENT_FIRST_RUN_IDS: tuple[str, ...] = (
    "marketing-ops",
    "lead-waterfall",
    "rnd-dev",
    "finance-ops",
    "digital-ops",
    "product-ship",
)

CORE_FIRST_RUN_TEMPLATE_IDS: tuple[str, ...] = ("marketing-ops", "lead-waterfall", "rnd-dev")


class VirtualCompanyProfilePublic(BaseModel):
    """Operator profile injected into swarm HiveMind context."""

    model_config = ConfigDict(extra="forbid")

    brand_name: str = Field(default="", max_length=160)
    industry: str = Field(default="", max_length=160)
    focus_areas: list[str] = Field(default_factory=list, max_length=12)
    risk_tolerance: RiskTolerance = "medium"
    primary_goal: str = Field(default="", max_length=512)
    onboarded: bool = False


class VirtualCompanyProfilePatch(BaseModel):
    """Partial profile update from dashboard."""

    model_config = ConfigDict(extra="forbid")

    brand_name: str | None = Field(default=None, max_length=160)
    industry: str | None = Field(default=None, max_length=160)
    focus_areas: list[str] | None = Field(default=None, max_length=12)
    risk_tolerance: RiskTolerance | None = None
    primary_goal: str | None = Field(default=None, max_length=512)


def _profile_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(VIRTUAL_COMPANY_PROFILE_BUCKET)
    return dict(bucket) if isinstance(bucket, dict) else {}


def profile_from_tenant(tenant: Tenant | None) -> VirtualCompanyProfilePublic:
    """Read stored operator profile."""

    bucket = _profile_bucket(tenant.operator_settings if tenant is not None else None)
    focus_raw = bucket.get("focus_areas")
    focus = [str(x).strip() for x in focus_raw if str(x).strip()] if isinstance(focus_raw, list) else []
    risk = str(bucket.get("risk_tolerance") or "medium").strip().lower()
    if risk not in {"low", "medium", "high"}:
        risk = "medium"
    brand = str(bucket.get("brand_name") or "").strip()
    industry = str(bucket.get("industry") or "").strip()
    goal = str(bucket.get("primary_goal") or "").strip()
    onboarded = bool(brand and industry and goal)
    return VirtualCompanyProfilePublic(
        brand_name=brand,
        industry=industry,
        focus_areas=focus[:12],
        risk_tolerance=risk,  # type: ignore[arg-type]
        primary_goal=goal,
        onboarded=onboarded,
    )


def merge_profile_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial virtual company profile patch."""

    root = dict(operator_settings or {})
    bucket = _profile_bucket(root)
    if "brand_name" in patch and patch["brand_name"] is not None:
        bucket["brand_name"] = str(patch["brand_name"]).strip()[:160]
    if "industry" in patch and patch["industry"] is not None:
        bucket["industry"] = str(patch["industry"]).strip()[:160]
    if "focus_areas" in patch and patch["focus_areas"] is not None:
        raw = patch["focus_areas"]
        bucket["focus_areas"] = [str(x).strip()[:64] for x in raw if str(x).strip()][:12]
    if "risk_tolerance" in patch and patch["risk_tolerance"] is not None:
        risk = str(patch["risk_tolerance"]).strip().lower()
        bucket["risk_tolerance"] = risk if risk in {"low", "medium", "high"} else "medium"
    if "primary_goal" in patch and patch["primary_goal"] is not None:
        bucket["primary_goal"] = str(patch["primary_goal"]).strip()[:512]
    root[VIRTUAL_COMPANY_PROFILE_BUCKET] = bucket
    return root


def profile_context_block(profile: VirtualCompanyProfilePublic) -> str:
    """Compact block for supervisor / swarm local_memory."""

    if not profile.onboarded:
        return ""
    areas = ", ".join(profile.focus_areas) if profile.focus_areas else "general"
    return (
        f"Operator profile: brand={profile.brand_name}; industry={profile.industry}; "
        f"focus={areas}; risk={profile.risk_tolerance}; goal={profile.primary_goal[:200]}"
    )


async def build_bootstrap_checklist(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    dashboard_user_id: object,
) -> dict[str, Any]:
    """Free-first readiness: profile, routing, connectors per department."""

    profile = profile_from_tenant(tenant)
    routing = await load_routing_config(session, tenant_id=tenant.id if tenant is not None else None)
    svc = DynamicConnectorService()
    rows = await svc.list_visible(session, dashboard_user_id=dashboard_user_id)  # type: ignore[arg-type]
    installed_rows = {
        row.slug.strip().lower()
        for row in rows
        if not row.is_builtin
    }
    installed_active = {
        row.slug.strip().lower()
        for row in rows
        if row.is_active and not row.is_builtin
    }

    connectors: list[dict[str, Any]] = []
    for slug in sorted(ALL_SUGGESTED_CONNECTORS):
        connectors.append(
            {
                "slug": slug,
                "installed": slug in installed_rows,
                "installed_active": slug in installed_active,
                "oauth_provider": OAUTH_PROVIDER_BY_CONNECTOR_SLUG.get(slug),
                "departments": [dept for dept, slugs in DEPARTMENT_CONNECTOR_MAP.items() if slug in slugs],
            },
        )

    departments = [
        {
            "id": dept_id,
            "connectors_installed": all(s in installed_rows for s in slugs),
            "connectors_ready": all(s in installed_active for s in slugs),
            "missing_connectors": [s for s in slugs if s not in installed_rows],
            "pending_oauth": [s for s in slugs if s in installed_rows and s not in installed_active],
        }
        for dept_id, slugs in DEPARTMENT_CONNECTOR_MAP.items()
    ]

    routing_mode = str(routing.get("routing_mode") or "quality")
    free_first = routing_mode == "free_first"

    from app.application.services.super_tool_router import list_super_tool_routers
    from app.application.services.virtual_company_swarm_builder import (
        VIRTUAL_COMPANY_TEMPLATE_IDS,
        list_built_wizard_templates,
    )

    routers = list_super_tool_routers(tenant)
    solo_router_slugs = {row["slug"] for row in SOLO_SUPER_ROUTER_PROVISION}
    provisioned_solo = [r for r in routers if r.slug in solo_router_slugs]
    active_solo = [r for r in provisioned_solo if r.is_active]

    built_templates = await list_built_wizard_templates(session)
    dept_swarms_built = sum(1 for tid in built_templates if tid in VIRTUAL_COMPANY_TEMPLATE_IDS)

    first_run = await build_first_run_status(session, tenant_id=tenant.id if tenant is not None else None)
    oauth_env = oauth_vendor_env_status()
    oauth_progress = build_oauth_progress(connectors=connectors, oauth_env=oauth_env)

    ready_count = sum(1 for d in departments if d["connectors_ready"])
    readiness_score = _readiness_score(
        profile=profile,
        free_first=free_first,
        connectors=connectors,
        super_routers_provisioned=len(provisioned_solo),
        super_routers_active=len(active_solo),
        dept_swarms_built=dept_swarms_built,
        first_run=first_run,
    )
    simulate_path_complete = _simulate_path_complete(
        profile=profile,
        free_first=free_first,
        solo_routers_provisioned=len(provisioned_solo),
        dept_swarms_built=dept_swarms_built,
        first_run=first_run,
    )
    blockers = _blockers(
        profile,
        free_first,
        ready_count,
        len(provisioned_solo),
        dept_swarms_built,
        first_run,
        simulate_path_complete=simulate_path_complete,
    )
    optional_next = _optional_next_steps(simulate_path_complete=simulate_path_complete, oauth_progress=oauth_progress)
    return {
        "profile": profile.model_dump(),
        "profile_complete": profile.onboarded,
        "routing_mode": routing_mode,
        "free_first_recommended": True,
        "free_first_active": free_first,
        "connectors": connectors,
        "departments": departments,
        "departments_ready": ready_count,
        "departments_total": len(departments),
        "super_routers": {
            "provisioned": len(provisioned_solo),
            "provisioned_total": len(SOLO_SUPER_ROUTER_PROVISION),
            "active": len(active_solo),
            "slugs": [r.slug for r in provisioned_solo],
        },
        "swarms": {
            "built_templates": built_templates,
            "departments_built": dept_swarms_built,
            "departments_total": len(VIRTUAL_COMPANY_TEMPLATE_IDS),
            "sentinel_built": "sentinel-radar" in built_templates,
        },
        "first_run": first_run,
        "oauth_progress": oauth_progress,
        "readiness_score": readiness_score,
        "simulate_path_complete": simulate_path_complete,
        "blockers": blockers,
        "optional_next_steps": optional_next,
        "sentinel_recommended": True,
        "next_steps": blockers + optional_next,
    }


def _simulate_path_complete(
    *,
    profile: VirtualCompanyProfilePublic,
    free_first: bool,
    solo_routers_provisioned: int,
    dept_swarms_built: int,
    first_run: dict[str, Any],
) -> bool:
    """True when simulate-only Virtual Company bootstrap is finished (connectors optional)."""

    return (
        profile.onboarded
        and free_first
        and solo_routers_provisioned >= len(SOLO_SUPER_ROUTER_PROVISION)
        and dept_swarms_built >= len(DEPARTMENT_CONNECTOR_MAP)
        and bool(first_run.get("all_department_first_runs_completed"))
    )


def _blockers(
    profile: VirtualCompanyProfilePublic,
    free_first: bool,
    dept_ready: int,
    solo_routers_provisioned: int,
    dept_swarms_built: int,
    first_run: dict[str, Any],
    *,
    simulate_path_complete: bool,
) -> list[str]:
    """Required steps before simulate path is considered complete."""

    steps: list[str] = []
    if not profile.onboarded:
        steps.append("Complete Virtual Company profile in Swarm Builder.")
    if not free_first:
        steps.append("Set LLM routing to free_first in Settings → Costs (solo €0 target).")
    if solo_routers_provisioned < len(SOLO_SUPER_ROUTER_PROVISION):
        steps.append("Provision solo Super Tool Routers in Execution Studio setup.")
    if dept_swarms_built < len(DEPARTMENT_CONNECTOR_MAP):
        steps.append("Build department swarms — use Build all 6 + Sentinel in setup card.")
    if not first_run.get("all_department_first_runs_completed"):
        steps.append(
            f"Run department first simulate sessions ({first_run.get('completed_count', 0)}/"
            f"{first_run.get('playbooks_total', len(FIRST_RUN_PLAYBOOKS))} done) — setup card or "
            "./scripts/operator-start-all-first-runs.sh"
        )
    elif not simulate_path_complete and dept_ready < len(DEPARTMENT_CONNECTOR_MAP):
        steps.append(
            "Configure OAuth in .env.prod.oauth, or manual tokens: "
            "./scripts/operator-vc-manual-tokens.sh (gh auth works for GitHub)."
        )
    return steps


def _optional_next_steps(
    *,
    simulate_path_complete: bool,
    oauth_progress: dict[str, Any],
) -> list[str]:
    """Deferred operator steps (live connectors) — not required for simulate mode."""

    if not simulate_path_complete:
        return []
    connected = int(oauth_progress.get("connected") or 0)
    total = int(oauth_progress.get("total") or 3)
    if connected >= total:
        return ["All live connectors active — Virtual Company at full readiness."]
    return [
        "Simulate path complete — live connectors optional until you need Notion/Gmail.",
        "When ready: NOTION_INTEGRATION_TOKEN → ./scripts/operator-vc-notion-onboard.sh (~88%).",
        "Gmail: OAUTH_GOOGLE_* in .env.prod.oauth → ./scripts/operator-oauth-redeploy.sh.",
    ]


async def build_first_run_status(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Track first-run playbook completion per template."""

    from sqlalchemy import desc, select

    from app.infrastructure.persistence.models.recipe import Recipe
    from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

    if tenant_id is None:
        return {"marketing_ops_completed": False, "completed_templates": [], "sessions": []}

    stmt = (
        select(SupervisorSession)
        .where(SupervisorSession.tenant_id == tenant_id)
        .order_by(desc(SupervisorSession.created_at))
        .limit(40)
    )
    rows = list((await session.execute(stmt)).scalars().all())

    sessions_out: list[dict[str, Any]] = []
    completed_templates: set[str] = set()

    for template_id, playbook in FIRST_RUN_PLAYBOOKS.items():
        needle = str(playbook.get("goal") or "")[:80].lower()
        for row in rows:
            ctx = row.context_summary if isinstance(row.context_summary, dict) else {}
            goal_blob = f"{row.goal} {ctx.get('raw_goal', '')}".lower()
            if needle and needle[:48] in goal_blob and row.status == "completed":
                completed_templates.add(template_id)
                sessions_out.append(
                    {
                        "template_id": template_id,
                        "session_id": str(row.id),
                        "status": row.status,
                        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    },
                )
                break

    # Recipe fallback — when verified `* first simulate` recipes exist (e.g.
    # operator-save-vc-playbooks.sh ran without an active supervisor session),
    # treat the template as completed.
    if len(completed_templates) < len(FIRST_RUN_PLAYBOOKS):
        recipe_titles = {
            "marketing-ops": "marketing ops",
            "lead-waterfall": "sales ops",
            "rnd-dev": "r&d",
            "finance-ops": "finance ops",
            "digital-ops": "digital ops",
            "product-ship": "product ship",
            "life-os": "life os",
        }
        recipe_rows = list(
            (
                await session.execute(
                    select(Recipe).where(Recipe.verified_at.isnot(None)).order_by(desc(Recipe.created_at)).limit(60)
                )
            )
            .scalars()
            .all()
        )
        for template_id, needle in recipe_titles.items():
            if template_id in completed_templates:
                continue
            for r in recipe_rows:
                name_low = (r.name or "").lower()
                if needle in name_low and "first simulate" in name_low:
                    completed_templates.add(template_id)
                    sessions_out.append(
                        {
                            "template_id": template_id,
                            "session_id": None,
                            "status": "verified-recipe",
                            "completed_at": r.verified_at.isoformat() if r.verified_at else None,
                            "recipe_id": str(r.id),
                        }
                    )
                    break

    return {
        "marketing_ops_completed": "marketing-ops" in completed_templates,
        "core_first_runs_completed": all(t in completed_templates for t in CORE_FIRST_RUN_TEMPLATE_IDS),
        "all_department_first_runs_completed": all(t in completed_templates for t in VC_DEPARTMENT_FIRST_RUN_IDS),
        "life_os_first_run_completed": "life-os" in completed_templates,
        "completed_count": len(completed_templates & set(VC_DEPARTMENT_FIRST_RUN_IDS)),
        "playbooks_total": len(VC_DEPARTMENT_FIRST_RUN_IDS),
        "completed_templates": sorted(completed_templates),
        "sessions": sessions_out,
    }


def _readiness_score(
    *,
    profile: VirtualCompanyProfilePublic,
    free_first: bool,
    connectors: list[dict[str, Any]],
    super_routers_provisioned: int,
    super_routers_active: int,
    dept_swarms_built: int,
    first_run: dict[str, Any],
) -> int:
    """0–100 Virtual Company solo readiness."""

    points = 0
    if profile.onboarded:
        points += 15
    if free_first:
        points += 10
    if connectors and all(c.get("installed") for c in connectors):
        points += 15
    if connectors:
        active_count = sum(1 for c in connectors if c.get("installed_active"))
        points += int(20 * active_count / max(len(connectors), 1))
    if super_routers_provisioned >= len(SOLO_SUPER_ROUTER_PROVISION):
        points += 10
    if super_routers_provisioned > 0:
        points += int(10 * super_routers_active / len(SOLO_SUPER_ROUTER_PROVISION))
    if dept_swarms_built >= len(DEPARTMENT_CONNECTOR_MAP):
        points += 10
    if first_run.get("core_first_runs_completed"):
        points += 10
    return min(100, points)


def build_oauth_progress(
    *,
    connectors: list[dict[str, Any]],
    oauth_env: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Solo Virtual Company OAuth vendor progress (env + active connectors)."""

    env = oauth_env if oauth_env is not None else oauth_vendor_env_status()
    vendor_keys = ("notion_workspace", "google_gmail", "github_rest")
    slug_by_vendor = {
        "notion_workspace": "notion_workspace",
        "google_gmail": "gmail_workspace",
        "github_rest": "github_rest",
    }
    configured = sum(1 for key in vendor_keys if env.get(key))
    connected = 0
    for key in vendor_keys:
        slug = slug_by_vendor.get(key, "")
        for row in connectors:
            if row.get("slug") == slug and row.get("installed_active"):
                connected += 1
                break
    return {
        "configured": configured,
        "connected": connected,
        "total": len(vendor_keys),
        "env_ready": configured >= len(vendor_keys),
        "connectors_ready": connected >= len(vendor_keys),
    }


def oauth_vendor_env_status() -> dict[str, bool]:
    """Whether OAuth client credentials are configured server-side."""

    from app.application.services.oauth_consent.providers import oauth_catalog_snapshot
    from app.core.config import get_settings

    snap = oauth_catalog_snapshot(get_settings())
    providers = snap.get("providers")
    out: dict[str, bool] = {}
    if isinstance(providers, list):
        for row in providers:
            if isinstance(row, dict) and row.get("provider_key"):
                out[str(row["provider_key"])] = bool(row.get("configured"))
    return out


def build_oauth_setup_guide() -> dict[str, Any]:
    """Operator checklist for solo Virtual Company OAuth vendor apps."""

    from app.core.config import get_settings

    settings = get_settings()
    env_status = oauth_vendor_env_status()
    vendors: list[dict[str, Any]] = [
        {
            "provider_key": "notion_workspace",
            "label": "Notion",
            "env_id": "OAUTH_NOTION_CLIENT_ID",
            "env_secret": "OAUTH_NOTION_CLIENT_SECRET",
            "console_url": "https://www.notion.so/profile/integrations",
            "scopes_hint": "Public integration · redirect URI below",
            "configured": env_status.get("notion_workspace", False),
        },
        {
            "provider_key": "google_gmail",
            "label": "Google (Gmail)",
            "env_id": "OAUTH_GOOGLE_CLIENT_ID",
            "env_secret": "OAUTH_GOOGLE_CLIENT_SECRET",
            "console_url": "https://console.cloud.google.com/apis/credentials",
            "scopes_hint": "gmail.modify · OAuth consent screen required",
            "configured": env_status.get("google_gmail", False),
        },
        {
            "provider_key": "github_rest",
            "label": "GitHub",
            "env_id": "OAUTH_GITHUB_CLIENT_ID",
            "env_secret": "OAUTH_GITHUB_CLIENT_SECRET",
            "console_url": "https://github.com/settings/developers",
            "scopes_hint": "OAuth App · repo read for PR lane",
            "configured": env_status.get("github_rest", False),
        },
    ]
    solo_ready = all(v["configured"] for v in vendors)
    return {
        "redirect_uri": settings.oauth_redirect_uri,
        "public_origin": settings.oauth_public_origin,
        "vendors": vendors,
        "all_configured": solo_ready,
        "env_file_hint": ".env.prod.oauth",
        "redeploy_hint": "./scripts/operator-oauth-redeploy.sh",
    }


def seed_default_operator_profile(tenant: Tenant) -> tuple[VirtualCompanyProfilePublic, bool]:
    """Idempotent: fill solo defaults when profile is not yet onboarded."""

    profile = profile_from_tenant(tenant)
    if profile.onboarded:
        return profile, False
    tenant.operator_settings = merge_profile_patch(tenant.operator_settings, DEFAULT_SOLO_PROFILE_PATCH)
    return profile_from_tenant(tenant), True


async def install_free_connectors(
    session: AsyncSession,
    *,
    dashboard_user_id: object,
) -> list[dict[str, Any]]:
    """Install Phase 3 Notion, Gmail, GitHub templates without secrets (OAuth completes in UI)."""

    results: list[dict[str, Any]] = []
    for slug, template_id in FREE_CONNECTOR_INSTALLS:
        status, connector = await install_marketplace_entry(
            session,
            dashboard_user_id=dashboard_user_id,  # type: ignore[arg-type]
            source="phase3_template",
            entry_id=template_id,
        )
        results.append(
            {
                "slug": slug,
                "template_id": template_id,
                "status": status,
                "oauth_provider": OAUTH_PROVIDER_BY_CONNECTOR_SLUG.get(slug),
                "connector_id": str(connector.id) if connector is not None else None,
            },
        )
    return results


async def provision_solo_super_routers(
    session: AsyncSession,
    *,
    tenant: Tenant,
    dashboard_user_id: object,
    activate_when_ready: bool = True,
) -> list[dict[str, Any]]:
    """Idempotent: create solo Super Tool Routers for Virtual Company departments."""

    from app.application.services.super_tool_router import (
        SuperToolRouterPatchBody,
        create_router_from_preset,
        list_super_tool_routers,
        patch_super_tool_router,
    )

    svc = DynamicConnectorService()
    rows = await svc.list_visible(session, dashboard_user_id=dashboard_user_id)  # type: ignore[arg-type]
    installed_active = {
        row.slug.strip().lower()
        for row in rows
        if row.is_active and not row.is_builtin
    }

    existing = {router.slug: router for router in list_super_tool_routers(tenant)}
    results: list[dict[str, Any]] = []

    for spec in SOLO_SUPER_ROUTER_PROVISION:
        slug = spec["slug"]
        preset_id = spec["preset_id"]
        if slug in existing:
            router = existing[slug]
            status = "already_exists"
        else:
            router = await create_router_from_preset(
                session,
                tenant=tenant,
                preset_id=preset_id,
                slug=slug,
                name=spec["name"],
            )
            existing[slug] = router
            status = "created"

        activated = False
        if activate_when_ready and not router.is_active:
            needed = {s.strip().lower() for s in router.connector_slugs if s.strip()}
            partial_min = SOLO_ROUTER_PARTIAL_MIN_CONNECTORS.get(slug, needed)
            if needed.issubset(installed_active) or partial_min.issubset(installed_active):
                router = await patch_super_tool_router(
                    session,
                    tenant=tenant,
                    router_id=uuid.UUID(router.id),
                    body=SuperToolRouterPatchBody(is_active=True),
                )
                activated = True
                status = f"{status}_activated" if status != "created" else "created_activated"

        results.append(
            {
                "slug": slug,
                "preset_id": preset_id,
                "status": status,
                "is_active": router.is_active,
                "activated": activated,
            },
        )
    return results


def first_run_playbook(template_id: str) -> dict[str, Any] | None:
    """Guided first supervisor session for a department wizard template."""

    key = template_id.strip().lower()
    row = FIRST_RUN_PLAYBOOKS.get(key)
    if row is None:
        return None
    return {"template_id": key, **row}


async def start_first_run_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    template_id: str,
    created_by_subject: str | None,
) -> dict[str, Any]:
    """Create supervisor session from first-run playbook."""

    from app.application.services.supervisor.session_service import create_supervisor_session
    from app.application.services.supervisor.shared_context import SharedContextService

    playbook = first_run_playbook(template_id)
    if playbook is None:
        msg = f"unknown template_id:{template_id.strip().lower()}"
        raise KeyError(msg)

    created = await create_supervisor_session(
        session,
        goal=str(playbook["goal"]),
        created_by_subject=created_by_subject,
        runtime_mode=str(playbook.get("runtime_mode") or "durable"),
        roles=list(playbook.get("roles") or []),
        shared_context=SharedContextService(),
        retrieval_contract="customer_history+policy+last_3_tasks",
        skill_slugs=list(playbook.get("skills") or []),
        tenant_id=tenant_id,
    )
    await session.commit()
    return {
        "session_id": str(created.id),
        "template_id": playbook["template_id"],
        "goal_preview": str(playbook["goal"])[:160],
        "status": str(created.status),
    }


async def apply_solo_free_first_bootstrap(session: AsyncSession, *, tenant: Tenant) -> dict[str, Any]:
    """Idempotent solo bootstrap: free_first routing if not already set."""

    routing = await load_routing_config(session, tenant_id=tenant.id)
    current = str(routing.get("routing_mode") or "quality")
    changed = False
    if current != "free_first":
        tenant.operator_settings = merge_routing_patch(
            tenant.operator_settings,
            {"routing_mode": normalize_routing_mode("free_first")},
        )
        changed = True
        await session.flush()
    return {"routing_mode": "free_first", "changed": changed}


__all__ = [
    "ALL_SUGGESTED_CONNECTORS",
    "DEFAULT_SOLO_PROFILE_PATCH",
    "DEPARTMENT_CONNECTOR_MAP",
    "FREE_CONNECTOR_INSTALLS",
    "OAUTH_PROVIDER_BY_CONNECTOR_SLUG",
    "VirtualCompanyProfilePatch",
    "VirtualCompanyProfilePublic",
    "apply_solo_free_first_bootstrap",
    "build_bootstrap_checklist",
    "build_first_run_status",
    "build_oauth_setup_guide",
    "first_run_playbook",
    "install_free_connectors",
    "merge_profile_patch",
    "oauth_vendor_env_status",
    "profile_context_block",
    "profile_from_tenant",
    "provision_solo_super_routers",
    "seed_default_operator_profile",
    "start_first_run_session",
]
