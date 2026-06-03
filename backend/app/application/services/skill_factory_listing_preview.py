"""Monid listing preview enrichment when operator approves Skill Factory forge."""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_pack_video_hook import (
    extract_monid_video_url_from_upstream,
    monid_video_bucket_from_operator_settings,
)
from app.application.services.skill_factory_service import SkillFactoryPolicyOut, get_skill_factory_policy
from app.application.services.skill_market_intel_monid import gather_monid_listing_signals, monid_connector_ready
from app.core.config import settings
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

_MONID_SLUG = "monid_mcp"


def _append_listing_preview_ref(
    opportunity: SkillOpportunityORM,
    *,
    hook: str,
    source: str,
    video_preview_url: str | None = None,
) -> None:
    """Merge listing preview into opportunity source_refs (idempotent-ish)."""

    refs: list[Any] = list(opportunity.source_refs or [])
    refs = [item for item in refs if not (isinstance(item, dict) and item.get("kind") == "listing_preview")]
    refs.append(
        {
            "kind": "listing_preview",
            "hook": hook[:400],
            "source": source,
            "video_preview_url": video_preview_url,
        },
    )
    opportunity.source_refs = refs[:24]


def _provider_endpoint_from_refs(refs: list[dict[str, Any]]) -> tuple[str, str]:
    """Pick first Monid discover ref with provider + endpoint."""

    for item in refs:
        provider = str(item.get("provider") or "").strip()
        endpoint = str(item.get("endpoint") or "").strip()
        if provider and endpoint:
            return provider, endpoint
    return "", ""


def _build_skill_video_input(*, title: str, niche: str, hook: str) -> dict[str, Any]:
    """Prompt payload for Gumroad teaser video via Monid run."""

    prompt = (
        f"15 second Gumroad product preview video for AI agent skill pack: {title}. "
        f"Niche: {niche}. Hook: {hook[:200]}. Show workflow outcome, neon-dark tech aesthetic."
    )
    return {"prompt": prompt[:500], "duration_sec": 15}


async def _resolve_monid_provider_endpoint(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    discover_refs: list[dict[str, Any]],
) -> tuple[str, str]:
    """Resolve Monid provider/endpoint from tenant config or discover."""

    bucket = monid_video_bucket_from_operator_settings(tenant.operator_settings if tenant is not None else None)
    provider = str(bucket.get("provider") or "").strip()
    endpoint = str(bucket.get("endpoint") or "").strip()
    if provider and endpoint:
        return provider, endpoint

    provider, endpoint = _provider_endpoint_from_refs(discover_refs)
    if provider and endpoint:
        return provider, endpoint

    from app.application.services.execution_studio import execute_studio_tool

    discover = await execute_studio_tool(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        connector_slug=_MONID_SLUG,
        tool_name="discover",
        arguments={"query": "short form video generation gumroad product preview", "limit": 5},
        mode="live",
        operator_confirmed=True,
    )
    if not discover.get("ok"):
        return "", ""
    raw = str(discover.get("result") or "")
    try:
        payload = json.loads(raw) if raw.startswith("{") else {}
    except json.JSONDecodeError:
        payload = {}
    endpoints = payload.get("endpoints") if isinstance(payload.get("endpoints"), list) else []
    for item in endpoints:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or provider).strip()
        endpoint = str(item.get("endpoint") or endpoint).strip()
        if provider and endpoint:
            return provider, endpoint
    return "", ""


async def _maybe_run_monid_video_preview(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    title: str,
    niche: str,
    hook: str,
    discover_refs: list[dict[str, Any]],
) -> str | None:
    """Run Monid video generation when enabled (pay-per-call, Execution Studio governed)."""

    if not settings.skill_factory_monid_video_preview_enabled:
        return None

    provider, endpoint = await _resolve_monid_provider_endpoint(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        discover_refs=discover_refs,
    )
    if not provider or not endpoint:
        logger.warning(
            "skill_factory.listing_video_no_endpoint",
            agent_id="skill_factory",
        )
        return None

    bucket = monid_video_bucket_from_operator_settings(tenant.operator_settings if tenant is not None else None)
    template = dict(bucket.get("input_template") or {})
    if template:
        run_input: dict[str, Any] = {}
        for key, value in template.items():
            text = str(value)
            text = text.replace("{{title}}", title).replace("{{body}}", hook[:500]).replace("{{niche}}", niche)
            run_input[str(key)] = text
    else:
        run_input = _build_skill_video_input(title=title, niche=niche, hook=hook)

    from app.application.services.execution_studio import execute_studio_tool

    upstream = await execute_studio_tool(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        connector_slug=_MONID_SLUG,
        tool_name="run",
        arguments={"provider": provider, "endpoint": endpoint, "input": run_input},
        mode="live",
        operator_confirmed=True,
    )
    if not upstream.get("ok"):
        logger.warning(
            "skill_factory.listing_video_run_failed",
            agent_id="skill_factory",
            error=str(upstream.get("error") or "")[:200],
        )
        return None

    url = extract_monid_video_url_from_upstream(upstream)
    if url:
        logger.info(
            "skill_factory.listing_video_applied",
            agent_id="skill_factory",
            video_preview_url=url[:120],
        )
    return url


async def maybe_enrich_listing_preview_on_approve(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunity: SkillOpportunityORM | None,
    title: str,
    policy: SkillFactoryPolicyOut | None = None,
    tenant: Tenant | None = None,
    dashboard_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Run Monid discover (and optional video run) on approve for Gumroad LISTING export."""

    if opportunity is None:
        return {"skipped": True, "reason": "no_opportunity"}

    active_policy = policy or await get_skill_factory_policy(session, tenant_id=tenant_id)
    if not active_policy.monid_listing_preview_on_approve:
        return {"skipped": True, "reason": "policy_disabled"}
    if not await monid_connector_ready(session):
        return {"skipped": True, "reason": "monid_not_ready"}

    niche = str(opportunity.niche or title)
    refs = await gather_monid_listing_signals(session, tenant_id=tenant_id, niche=f"{title} {niche} gumroad listing")
    hook = ""
    if refs:
        hook = str(refs[0].get("excerpt") or "").strip()
    if not hook:
        hook = f"Verified AI agent skill — {title}"[:240]

    video_url: str | None = None
    if (
        active_policy.monid_listing_video_preview_on_approve
        and dashboard_user_id is not None
    ):
        video_url = await _maybe_run_monid_video_preview(
            session,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            title=title,
            niche=niche,
            hook=hook,
            discover_refs=refs,
        )

    source = "monid_discover_approve"
    if video_url:
        source = "monid_discover_approve+video"

    _append_listing_preview_ref(
        opportunity,
        hook=hook,
        source=source,
        video_preview_url=video_url,
    )
    await session.flush()
    logger.info(
        "skill_factory.listing_preview_enriched",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(opportunity.id),
        has_video=bool(video_url),
    )
    return {
        "ok": True,
        "hook": hook[:120],
        "video_preview_url": video_url,
    }


__all__ = ["maybe_enrich_listing_preview_on_approve"]
