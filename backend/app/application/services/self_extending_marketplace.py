"""Self-extending tool marketplace — Forager proposals → one-click MCP preset install."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_intelligence import run_intelligence_scan
from app.application.services.tool_marketplace import install_marketplace_entry, marketplace_catalog
from app.core.config import settings
from app.infrastructure.connectors.phase3.catalog import get_phase3_template, iter_phase3_templates


class SelfExtendingMarketplaceDisabledError(RuntimeError):
    """Raised when the self-extending marketplace feature flag is off."""


class SelfExtendingUnsupportedProposalError(ValueError):
    """Raised when a proposal kind cannot be applied automatically."""


class SelfExtendingUnknownTemplateError(KeyError):
    """Raised when the Phase3 template id is unknown."""


def _installed_slugs(catalog: dict[str, Any]) -> set[str]:
    rows = catalog.get("phase3_templates")
    if not isinstance(rows, list):
        return set()
    out: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not row.get("installed"):
            continue
        slug = str(row.get("slug") or "").strip().lower()
        if slug:
            out.add(slug)
    return out


def _enrich_proposal(
    proposal: dict[str, Any],
    *,
    templates_by_id: dict[str, Any],
    installed_slugs: set[str],
) -> dict[str, Any]:
    """Attach marketplace install metadata to one intelligence proposal."""

    item = dict(proposal)
    kind = str(item.get("kind") or "")
    target = str(item.get("target") or "")

    if kind != "mcp_preset_skill":
        item["action"] = "review"
        return item

    template = templates_by_id.get(target)
    if template is None:
        item.update(
            {
                "action": "review",
                "marketplace_source": None,
                "entry_id": target,
                "template_title": target.replace("_", " ").title(),
                "installed": False,
            },
        )
        return item

    slug = str(template.suggested_slug or "").strip().lower()
    item.update(
        {
            "action": "install_marketplace",
            "marketplace_source": "phase3_template",
            "entry_id": template.template_id,
            "template_title": template.title,
            "template_summary": template.summary,
            "suggested_slug": template.suggested_slug,
            "installed": slug in installed_slugs,
            "skill_doc_hint": f"backend/app/skills/patterns/{template.template_id.replace('_', '-')}.md",
        },
    )
    return item


async def build_enriched_intelligence_scan(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Run Forager scan and enrich MCP preset proposals with install actions."""

    base = run_intelligence_scan()
    templates_by_id = {template.template_id: template for template in iter_phase3_templates()}
    catalog = await marketplace_catalog(session, dashboard_user_id=dashboard_user_id)
    installed_slugs = _installed_slugs(catalog)

    proposals = [
        _enrich_proposal(
            proposal,
            templates_by_id=templates_by_id,
            installed_slugs=installed_slugs,
        )
        for proposal in base.get("proposals", [])
        if isinstance(proposal, dict)
    ]

    if tenant_id is not None:
        from app.application.services.tool_gap_signal import list_tool_gaps

        seen_targets = {
            str(row.get("target") or "")
            for row in proposals
            if str(row.get("kind") or "") == "mcp_preset_skill"
        }
        for gap in await list_tool_gaps(tenant_id=tenant_id, limit=8):
            template_id = str(gap.get("suggested_template_id") or "").strip()
            if not template_id or template_id in seen_targets:
                continue
            seen_targets.add(template_id)
            proposals.insert(
                0,
                _enrich_proposal(
                    {
                        "kind": "mcp_preset_skill",
                        "target": template_id,
                        "priority": "high",
                        "rationale": f"Tool gap from agent session: {str(gap.get('message') or '')[:180]}",
                    },
                    templates_by_id=templates_by_id,
                    installed_slugs=installed_slugs,
                ),
            )
    installable = sum(
        1
        for row in proposals
        if row.get("action") == "install_marketplace" and not bool(row.get("installed"))
    )

    return {
        **base,
        "proposals": proposals,
        "self_extending": {
            "enabled": bool(settings.self_extending_tool_marketplace_enabled),
            "installable_count": installable,
            "apply_path": "/api/v1/harness/intelligence-apply",
            "marketplace_path": "/integrations#tools",
        },
    }


async def apply_intelligence_proposal(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    kind: str,
    target: str,
) -> dict[str, Any]:
    """Apply one Forager proposal — currently MCP preset one-click install only."""

    if not settings.self_extending_tool_marketplace_enabled:
        msg = "Self-extending tool marketplace is disabled."
        raise SelfExtendingMarketplaceDisabledError(msg)

    normalized_kind = kind.strip().lower()
    entry_id = target.strip()
    if normalized_kind != "mcp_preset_skill":
        msg = f"Unsupported proposal kind: {kind}"
        raise SelfExtendingUnsupportedProposalError(msg)
    if not entry_id:
        msg = "Proposal target is required."
        raise SelfExtendingUnsupportedProposalError(msg)

    template = get_phase3_template(entry_id)
    result, connector = await install_marketplace_entry(
        session,
        dashboard_user_id=dashboard_user_id,
        source="phase3_template",
        entry_id=template.template_id,
    )
    payload: dict[str, Any] = {
        "status": result,
        "kind": normalized_kind,
        "target": template.template_id,
        "template_title": template.title,
        "suggested_slug": template.suggested_slug,
        "skill_doc_hint": f"backend/app/skills/patterns/{template.template_id.replace('_', '-')}.md",
    }
    if connector is not None:
        payload["connector"] = connector.model_dump(mode="json")
    return payload


def self_extending_marketplace_status() -> dict[str, Any]:
    """Non-secret deployment status for harness snapshot."""

    return {
        "enabled": bool(settings.self_extending_tool_marketplace_enabled),
        "scan_path": "/api/v1/harness/intelligence-scan",
        "apply_path": "/api/v1/harness/intelligence-apply",
        "supported_proposal_kinds": ["mcp_preset_skill"],
    }


__all__ = [
    "SelfExtendingMarketplaceDisabledError",
    "SelfExtendingUnknownTemplateError",
    "SelfExtendingUnsupportedProposalError",
    "apply_intelligence_proposal",
    "build_enriched_intelligence_scan",
    "self_extending_marketplace_status",
]
