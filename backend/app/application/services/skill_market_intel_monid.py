"""Monid listing/market signals for Skill Factory research (discover-only, low cost)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = structlog.get_logger(__name__)

_MONID_SLUG = "monid_mcp"

_LISTING_SIGNAL_RE = re.compile(
    r"\b(gumroad|github|marketplace|listing|skill|pack|template|workflow|video|tiktok|"
    r"social|sentiment|competitor|lead|price|demand|buyers?)\b",
    re.IGNORECASE,
)


def _parse_monid_discover_payload(raw: str, *, niche: str) -> list[dict[str, Any]]:
    """Extract market intel refs from Monid discover JSON/text."""

    refs: list[dict[str, Any]] = []
    payload: dict[str, Any] | list[Any] | None = None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = None

    endpoints: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        block = payload.get("endpoints")
        if isinstance(block, list):
            endpoints = [item for item in block if isinstance(item, dict)]
        elif isinstance(payload.get("results"), list):
            endpoints = [item for item in payload["results"] if isinstance(item, dict)]
    elif isinstance(payload, list):
        endpoints = [item for item in payload if isinstance(item, dict)]

    for item in endpoints[:10]:
        provider = str(item.get("provider") or item.get("name") or "")
        endpoint = str(item.get("endpoint") or item.get("path") or "")
        desc = str(item.get("description") or item.get("summary") or item.get("docs") or "")
        blob = f"{provider} {endpoint} {desc}".strip()
        if len(blob) < 12:
            continue
        if not _LISTING_SIGNAL_RE.search(blob):
            continue
        refs.append(
            {
                "kind": "external_monid_discover",
                "excerpt": f"Monid: {provider}/{endpoint} — {desc[:100]}".strip(" —"),
                "provider": provider[:80] or None,
                "endpoint": endpoint[:120] or None,
                "keyword_hits": len(_LISTING_SIGNAL_RE.findall(blob)),
            },
        )

    if not refs and _LISTING_SIGNAL_RE.search(raw):
        refs.append(
            {
                "kind": "external_monid_discover",
                "excerpt": f"Monid discover for {niche[:60]}: {raw.strip()[:140]}",
                "keyword_hits": len(_LISTING_SIGNAL_RE.findall(raw)),
            },
        )
    return refs


async def monid_connector_ready(session: AsyncSession | None) -> bool:
    """Return True when Monid MCP connector is active with credentials."""

    if session is None:
        return False
    from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=_MONID_SLUG)
    if row is None or not row.is_active:
        return False
    secrets = svc._secrets_dict(row)  # noqa: SLF001
    token = str(secrets.get("bearer_token") or secrets.get("api_key") or "").strip()
    return bool(token)


async def _persist_monid_intel_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    niche: str,
    refs: list[dict[str, Any]],
) -> None:
    """Persist Monid discover excerpts into Knowledge for HiveMind embed."""

    if not refs:
        return
    from app.infrastructure.persistence.models.knowledge import KnowledgeItem

    lines = [f"- {item.get('excerpt', '')}" for item in refs[:6] if item.get("excerpt")]
    if not lines:
        return
    blob = f"Skill market Monid intel — niche: {niche[:120]}\n\n" + "\n".join(lines)
    session.add(
        KnowledgeItem(
            tenant_id=tenant_id,
            source_type="skill_market_monid",
            source_url=f"monid://skill-factory/{niche[:80]}",
            content_text=blob[:12_000],
            confidence_score=0.73,
            topic_tags=["skill-market", "skill-market-intel", "monid", "listing-signals"],
            decay_factor=1.0,
            scraped_at=datetime.now(tz=UTC),
        ),
    )
    await session.flush()


async def gather_monid_listing_signals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    niche: str,
) -> list[dict[str, Any]]:
    """Run Monid discover for marketplace/listing endpoint hints (pay-per-call)."""

    if not settings.skill_factory_monid_intel_enabled:
        return []
    if not await monid_connector_ready(session):
        return []

    from app.infrastructure.connectors.dynamic.service import invoke_dynamic_tool

    query = (
        f"{niche.strip()} AI agent skill pack marketplace gumroad github listing "
        "competitor social sentiment"
    )[:320]
    raw = await invoke_dynamic_tool(
        session,
        connector_slug=_MONID_SLUG,
        tool_name="discover",
        arguments={"query": query, "limit": 8},
        manager_slug="research_intelligence",
        agent_task_id="skill_factory_monid_discover",
    )
    if raw.startswith("dynamic_invoke_error") or raw.startswith("dynamic_invoke_http"):
        logger.warning(
            "skill_market_intel_monid.discover_failed",
            agent_id="skill_market_intel_monid",
            swarm_id=str(tenant_id or ""),
            reason=raw[:120],
        )
        return []

    refs = _parse_monid_discover_payload(raw, niche=niche)
    if refs and tenant_id is not None:
        await _persist_monid_intel_rows(session, tenant_id=tenant_id, niche=niche, refs=refs)
        logger.info(
            "skill_market_intel_monid.discover_complete",
            agent_id="skill_market_intel_monid",
            swarm_id=str(tenant_id),
            niche=niche[:80],
            hits=len(refs),
        )
    return refs


__all__ = [
    "_parse_monid_discover_payload",
    "gather_monid_listing_signals",
    "monid_connector_ready",
]
