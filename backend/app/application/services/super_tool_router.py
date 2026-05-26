"""Tenant-scoped Super Tool Router configs — ordered connector stacks per manager lane."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

import asyncio
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

SUPER_ROUTER_BUCKET = "super_tool_routers"
RoutingMode = Literal["priority", "research_then_action", "parallel_hint"]

ROUTER_PRESETS: tuple[dict[str, Any], ...] = (
    {
        "preset_id": "deep_research",
        "title": "Deep Research",
        "description": "Monid discovery + Apify heavy scraping for verified external datasets.",
        "routing_mode": "research_then_action",
        "manager_slugs": ["research_intelligence", "review_quality"],
        "connector_slugs": ["monid_mcp", "apify_store"],
    },
    {
        "preset_id": "app_actions",
        "title": "App Actions",
        "description": "Composio Tool Router + Nango proxy for live SaaS actions.",
        "routing_mode": "priority",
        "manager_slugs": ["execution_operations", "content_creation"],
        "connector_slugs": ["composio_router", "nango_hub"],
    },
    {
        "preset_id": "enterprise_hybrid",
        "title": "Enterprise Hybrid",
        "description": "Research data (Monid) + business systems (Merge) + app actions (Composio).",
        "routing_mode": "research_then_action",
        "manager_slugs": ["research_intelligence", "execution_operations", "review_quality"],
        "connector_slugs": ["monid_mcp", "merge_agent_handler", "composio_router"],
    },
    {
        "preset_id": "solo_app_actions",
        "title": "Solo App Actions",
        "description": "Free OAuth — Notion + Gmail for marketing and sales execution lanes (simulate default).",
        "routing_mode": "priority",
        "manager_slugs": ["content_creation", "execution_operations", "review_quality"],
        "connector_slugs": ["notion_workspace", "gmail_workspace"],
    },
    {
        "preset_id": "solo_dev_workspace",
        "title": "Solo Dev Workspace",
        "description": "GitHub + Notion for R&D and product ship lanes (PR drafts, docs simulate).",
        "routing_mode": "priority",
        "manager_slugs": ["research_intelligence", "product_mission", "review_quality"],
        "connector_slugs": ["github_rest", "notion_workspace"],
    },
)

RESEARCH_CONNECTOR_SLUGS: frozenset[str] = frozenset(
    {
        "monid_mcp",
        "apify_store",
        "venice_mcp",
    },
)

COST_TIER_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}

logger = get_logger(__name__)


class SuperToolRouterPublic(BaseModel):
    """Dashboard projection for one super router."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    slug: str
    description: str = ""
    is_active: bool = True
    routing_mode: RoutingMode = "priority"
    manager_slugs: list[str] = Field(default_factory=list)
    connector_slugs: list[str] = Field(default_factory=list)
    max_cost_tier: Literal["low", "medium", "high"] | None = None
    fallback_builtin_search: bool = True


class SuperToolRouterCreateBody(BaseModel):
    """Create payload."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=160)
    slug: str = Field(..., min_length=2, max_length=128)
    description: str = Field(default="", max_length=1024)
    is_active: bool = True
    routing_mode: RoutingMode = "priority"
    manager_slugs: list[str] = Field(default_factory=list)
    connector_slugs: list[str] = Field(min_length=1)
    max_cost_tier: Literal["low", "medium", "high"] | None = None
    fallback_builtin_search: bool = True

    @field_validator("slug")
    @classmethod
    def slug_lower(cls, value: str) -> str:
        """Normalise slug."""

        cleaned = value.strip().lower()
        if any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in cleaned):
            msg = "slug may contain only lowercase alphanumerics hyphen underscore"
            raise ValueError(msg)
        return cleaned


class SuperToolRouterPatchBody(BaseModel):
    """Partial update."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1024)
    is_active: bool | None = None
    routing_mode: RoutingMode | None = None
    manager_slugs: list[str] | None = None
    connector_slugs: list[str] | None = None
    max_cost_tier: Literal["low", "medium", "high"] | None = None
    fallback_builtin_search: bool | None = None


def _bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    raw = root.get(SUPER_ROUTER_BUCKET)
    return dict(raw) if isinstance(raw, dict) else {}


def _normalize_manager_slugs(values: list[str]) -> list[str]:
    return sorted({item.strip().lower() for item in values if item.strip()})


def _normalize_connector_slugs(values: list[str]) -> list[str]:
    return [item.strip().lower() for item in values if item.strip()]


def _row_to_public(row: dict[str, Any]) -> SuperToolRouterPublic:
    return SuperToolRouterPublic.model_validate(row)


def list_super_tool_routers(tenant: Tenant | None) -> list[SuperToolRouterPublic]:
    """Return all routers stored on the tenant."""

    bucket = _bucket(tenant.operator_settings if tenant is not None else None)
    items_raw = bucket.get("items")
    if not isinstance(items_raw, list):
        return []
    out: list[SuperToolRouterPublic] = []
    for row in items_raw:
        if isinstance(row, dict):
            try:
                out.append(_row_to_public(row))
            except ValueError:
                continue
    return sorted(out, key=lambda item: item.name.lower())


def resolve_router_connector_slugs(
    tenant: Tenant | None,
    *,
    manager_slug: str,
) -> tuple[str, ...]:
    """Merge active router connector slugs for a manager lane (router order preserved)."""

    lane = manager_slug.strip().lower()
    ordered: list[str] = []
    seen: set[str] = set()
    for router in list_super_tool_routers(tenant):
        if not router.is_active:
            continue
        managers = {m.strip().lower() for m in router.manager_slugs if m.strip()}
        if managers and lane not in managers:
            continue
        for slug in router.connector_slugs:
            key = slug.strip().lower()
            if key and key not in seen:
                seen.add(key)
                ordered.append(key)
    return tuple(ordered)


@dataclass(slots=True)
class RouterInvokePlan:
    """Runtime invoke plan for a manager lane."""

    routing_mode: RoutingMode
    connector_slugs: tuple[str, ...]
    fallback_builtin_search: bool = True
    router_slugs: tuple[str, ...] = ()
    max_cost_tier: Literal["low", "medium", "high"] | None = None


def connector_cost_tier_for_slug(connector_slug: str) -> str:
    """Resolve marketplace cost tier for a connector slug."""

    from app.infrastructure.connectors.phase3.catalog import iter_phase3_templates
    from app.infrastructure.connectors.phase3.marketplace_meta import marketplace_meta_for

    cleaned = connector_slug.strip().lower()
    for template in iter_phase3_templates():
        if template.suggested_slug.strip().lower() == cleaned:
            meta = marketplace_meta_for(template.template_id)
            tier = str(meta.get("cost_tier") or "medium").strip().lower()
            if tier in COST_TIER_RANK:
                return tier
    return "medium"


def is_connector_cost_allowed(*, connector_slug: str, max_cost_tier: str | None) -> bool:
    """Return True when connector cost tier is within router max cap."""

    if not max_cost_tier:
        return True
    cap = COST_TIER_RANK.get(max_cost_tier.strip().lower())
    if cap is None:
        return True
    tier = connector_cost_tier_for_slug(connector_slug)
    return COST_TIER_RANK.get(tier, 1) <= cap


def _strictest_cost_cap(
    routers: list[SuperToolRouterPublic],
) -> Literal["low", "medium", "high"] | None:
    """Pick strictest (lowest ceiling) max_cost_tier across matching routers."""

    caps = [row.max_cost_tier for row in routers if row.max_cost_tier]
    if not caps:
        return None
    return min(caps, key=lambda tier: COST_TIER_RANK.get(str(tier), 1))  # type: ignore[return-value]


def resolve_router_invoke_plan(
    tenant: Tenant | None,
    *,
    manager_slug: str,
) -> RouterInvokePlan | None:
    """Return merged invoke plan for active routers on a manager lane."""

    lane = manager_slug.strip().lower()
    if not lane:
        return None

    matching: list[SuperToolRouterPublic] = []
    for router in list_super_tool_routers(tenant):
        if not router.is_active:
            continue
        managers = {m.strip().lower() for m in router.manager_slugs if m.strip()}
        if managers and lane not in managers:
            continue
        matching.append(router)

    if not matching:
        return None

    slugs = resolve_router_connector_slugs(tenant, manager_slug=lane)
    if not slugs:
        return None

    mode: RoutingMode = matching[0].routing_mode
    fallback_search = any(bool(r.fallback_builtin_search) for r in matching)
    return RouterInvokePlan(
        routing_mode=mode,
        connector_slugs=slugs,
        fallback_builtin_search=fallback_search,
        router_slugs=tuple(r.slug for r in matching),
        max_cost_tier=_strictest_cost_cap(matching),
    )


def _manifest_tool_names(manifest: dict[str, Any]) -> list[str]:
    tools_blob = manifest.get("tools") if isinstance(manifest.get("tools"), list) else []
    names: list[str] = []
    for ent in tools_blob:
        if isinstance(ent, dict):
            cleaned = str(ent.get("name") or "").strip()
            if cleaned:
                names.append(cleaned)
    return names


def pick_fallback_tool_name(*, preferred: str, manifest: dict[str, Any]) -> str:
    """Pick a reasonable tool when falling back to another connector slug."""

    names = _manifest_tool_names(manifest)
    if not names:
        return preferred.strip() or "invoke"
    pref = preferred.strip()
    if pref and pref in names:
        return pref
    for token in ("discover", "search", "chat_completions", "invoke", "run"):
        for name in names:
            if token in name.lower():
                return name
    return names[0]


def _is_dynamic_invoke_error(result: str) -> bool:
    return str(result or "").startswith("dynamic_invoke_error:")


def partition_research_action_slugs(slugs: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Split router slugs into research vs action lanes for research_then_action mode."""

    research: list[str] = []
    action: list[str] = []
    for slug in slugs:
        if slug.strip().lower() in RESEARCH_CONNECTOR_SLUGS:
            research.append(slug)
        else:
            action.append(slug)
    return research, action


async def _invoke_one_slug(
    session: AsyncSession,
    *,
    svc: Any,
    slug: str,
    tool_name: str,
    arguments: dict[str, Any],
    manager_slug: str,
    agent_task_id: str,
    prefer_research_tool: bool = False,
    max_cost_tier: str | None = None,
) -> tuple[str, str, str]:
    """Invoke one connector; returns (slug, tool_pick, result)."""

    if not is_connector_cost_allowed(connector_slug=slug, max_cost_tier=max_cost_tier):
        tier = connector_cost_tier_for_slug(slug)
        return (
            slug,
            tool_name,
            f"dynamic_invoke_error: cost_tier_blocked ({tier} > max {max_cost_tier})",
        )

    from app.infrastructure.connectors.dynamic.hub import manifest_tool_default
    from app.infrastructure.connectors.dynamic.service import invoke_dynamic_tool

    row = await svc.fetch_by_slug(session, slug=slug)
    manifest = (
        dict(row.mcp_manifest)
        if row is not None and isinstance(row.mcp_manifest, dict)
        else manifest_tool_default()
    )
    if prefer_research_tool:
        tool_pick = pick_fallback_tool_name(preferred="discover", manifest=manifest)
    else:
        tool_pick = pick_fallback_tool_name(preferred=tool_name, manifest=manifest)
    result = await invoke_dynamic_tool(
        session,
        connector_slug=slug,
        tool_name=tool_pick,
        arguments=dict(arguments),
        manager_slug=manager_slug.strip().lower() or None,
        agent_task_id=agent_task_id,
    )
    return slug, tool_pick, result


async def invoke_mcp_with_router_fallback(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    manager_slug: str,
    connector_slug: str,
    tool_name: str,
    arguments: dict[str, Any],
    agent_task_id: str,
) -> str:
    """Invoke MCP tool using super router plan: priority, research_then_action, or parallel_hint."""

    from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

    primary = connector_slug.strip().lower()
    plan = resolve_router_invoke_plan(tenant, manager_slug=manager_slug)
    svc = DynamicConnectorService()
    cost_cap = plan.max_cost_tier if plan is not None else None

    if plan is None:
        _slug, _tool, result = await _invoke_one_slug(
            session,
            svc=svc,
            slug=primary,
            tool_name=tool_name,
            arguments=arguments,
            manager_slug=manager_slug,
            agent_task_id=agent_task_id,
            max_cost_tier=cost_cap,
        )
        return result

    if plan.routing_mode == "parallel_hint":
        slugs = list(dict.fromkeys([primary, *plan.connector_slugs]))

        async def _run(slug: str) -> str:
            _s, tool_pick, outcome = await _invoke_one_slug(
                session,
                svc=svc,
                slug=slug,
                tool_name=tool_name,
                arguments=arguments,
                manager_slug=manager_slug,
                agent_task_id=agent_task_id,
                max_cost_tier=cost_cap,
            )
            status = "ok" if not _is_dynamic_invoke_error(outcome) else "err"
            return f"### {slug}/{tool_pick} [{status}]\n{outcome[:1200]}"

        chunks = await asyncio.gather(*[_run(slug) for slug in slugs])
        return "parallel_router_results:\n" + "\n\n".join(chunks)

    if plan.routing_mode == "research_then_action":
        ordered = list(dict.fromkeys([*plan.connector_slugs]))
        research_slugs, action_slugs = partition_research_action_slugs(tuple(ordered))
        if primary in RESEARCH_CONNECTOR_SLUGS:
            if primary not in research_slugs:
                research_slugs.insert(0, primary)
        elif primary not in action_slugs:
            action_slugs.insert(0, primary)

        research_notes: list[str] = []
        for slug in research_slugs:
            _s, tool_pick, outcome = await _invoke_one_slug(
                session,
                svc=svc,
                slug=slug,
                tool_name=tool_name,
                arguments=arguments,
                manager_slug=manager_slug,
                agent_task_id=agent_task_id,
                prefer_research_tool=True,
                max_cost_tier=cost_cap,
            )
            if not _is_dynamic_invoke_error(outcome):
                research_notes.append(f"[{slug}/{tool_pick}] {outcome[:900]}")
            else:
                logger.info(
                    "super_router.research_phase_miss",
                    agent_id=agent_task_id,
                    swarm_id=slug,
                    task_id=manager_slug,
                )

        if not research_notes:
            return f"dynamic_invoke_error: research phase produced no verified data for `{primary}`"

        action_order = action_slugs or [primary]
        last_result = research_notes[-1]
        for slug in action_order:
            _s, tool_pick, outcome = await _invoke_one_slug(
                session,
                svc=svc,
                slug=slug,
                tool_name=tool_name,
                arguments=arguments,
                manager_slug=manager_slug,
                agent_task_id=agent_task_id,
                max_cost_tier=cost_cap,
            )
            if not _is_dynamic_invoke_error(outcome):
                ctx = "\n".join(research_notes[:3])
                return f"research_then_action_ok[{slug}/{tool_pick}]:\n## Research context\n{ctx}\n\n## Action result\n{outcome}"
            last_result = outcome
        return last_result

    # priority mode — sequential fallback
    try_order: list[str] = [primary]
    for slug in plan.connector_slugs:
        if slug not in try_order:
            try_order.append(slug)

    last_result = f"dynamic_invoke_error: connector `{primary}` inactive or unknown"
    for idx, slug in enumerate(try_order):
        _s, tool_pick, result = await _invoke_one_slug(
            session,
            svc=svc,
            slug=slug,
            tool_name=tool_name,
            arguments=arguments,
            manager_slug=manager_slug,
            agent_task_id=agent_task_id,
            max_cost_tier=cost_cap,
        )
        if not _is_dynamic_invoke_error(result):
            if idx > 0:
                return f"router_fallback_ok[{slug}/{tool_pick}]: {result}"
            return result
        last_result = result
        logger.info(
            "super_router.invoke_fallback",
            agent_id=agent_task_id,
            swarm_id=slug,
            task_id=manager_slug,
            attempt=idx + 1,
            routing_mode=plan.routing_mode,
        )
    return last_result


def _write_items(tenant: Tenant, items: list[dict[str, Any]]) -> dict[str, Any]:
    root = dict(tenant.operator_settings or {})
    bucket = _bucket(root)
    bucket["items"] = items
    root[SUPER_ROUTER_BUCKET] = bucket
    return root


async def create_super_tool_router(
    session: AsyncSession,
    *,
    tenant: Tenant,
    body: SuperToolRouterCreateBody,
) -> SuperToolRouterPublic:
    """Persist a new super router on the tenant."""

    items = [row.model_dump(mode="json") for row in list_super_tool_routers(tenant)]
    slug_key = body.slug.strip().lower()
    if any(str(row.get("slug", "")).strip().lower() == slug_key for row in items if isinstance(row, dict)):
        msg = "router slug already exists"
        raise ValueError(msg)

    row = SuperToolRouterPublic(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        slug=slug_key,
        description=body.description.strip(),
        is_active=body.is_active,
        routing_mode=body.routing_mode,
        manager_slugs=_normalize_manager_slugs(body.manager_slugs),
        connector_slugs=_normalize_connector_slugs(body.connector_slugs),
        max_cost_tier=body.max_cost_tier,
        fallback_builtin_search=body.fallback_builtin_search,
    )
    items.append(row.model_dump(mode="json"))
    tenant.operator_settings = _write_items(tenant, items)
    await session.commit()
    logger.info(
        "super_router.created",
        agent_id=str(tenant.id),
        swarm_id=row.slug,
        task_id="super-router",
    )
    return row


async def patch_super_tool_router(
    session: AsyncSession,
    *,
    tenant: Tenant,
    router_id: uuid.UUID,
    body: SuperToolRouterPatchBody,
) -> SuperToolRouterPublic:
    """Update one router row."""

    items_raw = [row.model_dump(mode="json") for row in list_super_tool_routers(tenant)]
    target_idx: int | None = None
    for idx, row in enumerate(items_raw):
        if str(row.get("id")) == str(router_id):
            target_idx = idx
            break
    if target_idx is None:
        msg = "router not found"
        raise ValueError(msg)

    current = SuperToolRouterPublic.model_validate(items_raw[target_idx])
    patch = body.model_dump(exclude_unset=True)
    if "manager_slugs" in patch and patch["manager_slugs"] is not None:
        patch["manager_slugs"] = _normalize_manager_slugs(patch["manager_slugs"])
    if "connector_slugs" in patch and patch["connector_slugs"] is not None:
        patch["connector_slugs"] = _normalize_connector_slugs(patch["connector_slugs"])
    updated = current.model_copy(update=patch)
    items_raw[target_idx] = updated.model_dump(mode="json")
    tenant.operator_settings = _write_items(tenant, items_raw)
    await session.commit()
    return updated


async def delete_super_tool_router(
    session: AsyncSession,
    *,
    tenant: Tenant,
    router_id: uuid.UUID,
) -> None:
    """Remove router from tenant settings."""

    kept = [row.model_dump(mode="json") for row in list_super_tool_routers(tenant) if row.id != str(router_id)]
    if len(kept) == len(list_super_tool_routers(tenant)):
        msg = "router not found"
        raise ValueError(msg)
    tenant.operator_settings = _write_items(tenant, kept)
    await session.commit()


async def create_router_from_preset(
    session: AsyncSession,
    *,
    tenant: Tenant,
    preset_id: str,
    slug: str,
    name: str | None = None,
) -> SuperToolRouterPublic:
    """Instantiate a router from a built-in preset."""

    preset = next((row for row in ROUTER_PRESETS if row["preset_id"] == preset_id.strip()), None)
    if preset is None:
        msg = f"unknown preset:{preset_id}"
        raise KeyError(msg)
    body = SuperToolRouterCreateBody(
        name=name or str(preset["title"]),
        slug=slug,
        description=str(preset.get("description") or ""),
        routing_mode=preset.get("routing_mode", "priority"),  # type: ignore[arg-type]
        manager_slugs=list(preset.get("manager_slugs") or []),
        connector_slugs=list(preset.get("connector_slugs") or []),
        is_active=False,
    )
    return await create_super_tool_router(session, tenant=tenant, body=body)
