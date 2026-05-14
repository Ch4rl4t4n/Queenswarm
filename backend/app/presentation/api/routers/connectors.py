"""Connector catalog, vault seals, OAuth refresh, and health pings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.presentation.api.deps import DashboardSession, DbSession
from app.infrastructure.connectors.mcp_adapter import MCPAdapter
from app.infrastructure.connectors.base import ConnectorAuthEnvelope
from app.infrastructure.connectors.oauth_refresh import exchange_refresh_token
from app.infrastructure.connectors.registry import registry
from app.infrastructure.connectors.secure_vault import CredentialPayload, vault_load_envelope, vault_upsert_credential
from app.infrastructure.connectors.dynamic.schemas import (
    DynamicConnectorCreateBody,
    DynamicConnectorPublic,
    DynamicConnectorSecretsInbound,
)
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.application.services.oauth_consent.providers import oauth_catalog_snapshot
from app.infrastructure.connectors.phase3.catalog import (
    PHASE3_TEMPLATE_INDEX,
    get_phase3_template,
    iter_phase3_templates,
    phase3_template_public_dict,
)
from app.infrastructure.connectors.phase3.obsidian_sync import obsidian_sync_snapshot, run_obsidian_vault_sync_once
from app.core.config import get_settings
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.logging import get_logger
from app.core.retry_external import retry_async_call

router = APIRouter()

logger = get_logger(__name__)


def _session_user_id(sess: dict[str, Any]) -> uuid.UUID:
    """Resolve Postgres ``dashboard_users.id`` from JWT ``sub``."""

    raw = sess.get("sub")
    if not isinstance(raw, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard credential missing.")
    parsed = parse_dashboard_user_subject(raw.strip())
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed dashboard subject.")
    return parsed


@router.get("/catalog", summary="List registered connector adapters + dynamic MCP manifests")
async def connectors_catalog(sess: DashboardSession, db: DbSession) -> dict[str, Any]:
    """Return slug ordering enriched with Postgres-backed dynamic MCP tool slots."""

    _ = sess
    merged_slugs = await registry.merged_slugs(db)
    manifests = await MCPAdapter.dynamic_tool_catalog(db)
    phase3_templates = [phase3_template_public_dict(row) for row in iter_phase3_templates()]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for payload in phase3_templates:
        grouped.setdefault(str(payload["category"]), []).append(payload)
    cfg = get_settings()
    return {
        "connectors": [{"slug": s} for s in merged_slugs],
        "static": [{"slug": s} for s in registry.slugs()],
        "mcp_manifest": manifests,
        "oauth_consent": oauth_catalog_snapshot(cfg),
        "phase3": {
            "template_count": len(PHASE3_TEMPLATE_INDEX),
            "template_ids": sorted(PHASE3_TEMPLATE_INDEX.keys()),
            "templates": phase3_templates,
            "grouped": grouped,
        },
    }


class VaultUpsertBody(BaseModel):
    """Operator-supplied plaintext secrets sealed into Postgres AES envelope."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    slug: str = Field(..., min_length=2, max_length=128)
    label: str | None = Field(default=None, max_length=256)
    oauth2_access_token: str | None = None
    oauth2_refresh_token: str | None = None
    oauth2_token_endpoint: str | None = None
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    api_key: str | None = None
    kind: Literal["oauth2", "api_key"]

    def to_payload(self) -> CredentialPayload:
        """Hydrate pydantic :class:`~app.connectors.secure_vault.CredentialPayload`."""

        if self.kind == "oauth2" and not (self.oauth2_access_token or self.oauth2_refresh_token):
            raise ValueError("OAuth2 credential requires access or refresh token.")
        if self.kind == "api_key" and not (self.api_key and self.api_key.strip()):
            raise ValueError("API key credential requires api_key.")
        return CredentialPayload(
            kind=self.kind,
            oauth2_access_token=self.oauth2_access_token,
            oauth2_refresh_token=self.oauth2_refresh_token,
            oauth2_token_endpoint=self.oauth2_token_endpoint,
            oauth2_client_id=self.oauth2_client_id,
            oauth2_client_secret=self.oauth2_client_secret,
            api_key=self.api_key,
            scopes=(),
        )


@router.post("/vault", summary="Upsert AES-sealed credential row for MCP / HTTP connectors")
async def connectors_vault_upsert(
    body: VaultUpsertBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, str]:
    """Persist ciphertext via :mod:`app.connectors.secure_vault`."""

    uid = _session_user_id(sess)
    try:
        payload = body.to_payload()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    await vault_upsert_credential(db, slug=body.slug, user_id=uid, payload=payload, label=body.label)
    return {"ok": "true", "slug": body.slug.strip().lower()}


class OAuthRefreshBody(BaseModel):
    """Thin refresh-client matching RFC6749-ish form posts."""

    grant_type: Literal["refresh_token"] = Field(default="refresh_token")
    connector_slug: str = Field(..., min_length=2, max_length=128)


@router.post("/oauth/token", summary="Refresh OAuth2 access tokens stored in vault")
async def connectors_oauth_refresh(
    body: OAuthRefreshBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    """Hydrate envelope, POST refresh upstream, persist updated ciphertext."""

    if body.grant_type != "refresh_token":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported grant_type")
    uid = _session_user_id(sess)
    env = await vault_load_envelope(db, slug=body.connector_slug.strip().lower(), user_id=uid)
    if env is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vault row missing.")
    try:
        payload, raw = await exchange_refresh_token(env)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"token_endpoint_error:{exc!s}",
        ) from exc
    await vault_upsert_credential(db, slug=body.connector_slug.strip().lower(), user_id=uid, payload=payload)
    return {"access_token": payload.oauth2_access_token, "token_type": "Bearer", "raw": raw}


class PingBody(BaseModel):
    """Optional inline secrets bypassing Postgres vault reads."""

    model_config = ConfigDict(extra="ignore")

    api_key: str | None = None
    oauth2_access_token: str | None = None


async def _resolve_envelope(
    *,
    body: PingBody | None,
    db: DbSession,
    uid: uuid.UUID,
    slug: str,
) -> ConnectorAuthEnvelope:
    """Hydrate bearer material for pings."""

    if body is not None:
        ak = body.api_key
        if isinstance(ak, str) and ak.strip():
            return ConnectorAuthEnvelope(kind="api_key", api_key=ak.strip())
        tok = body.oauth2_access_token
        if isinstance(tok, str) and tok.strip():
            return ConnectorAuthEnvelope(kind="oauth2", oauth2_access_token=tok.strip())
    loaded = await vault_load_envelope(db, slug=slug.strip().lower(), user_id=uid)
    if loaded is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vault credential missing.")
    return loaded


@router.post("/{slug}/ping", summary="Delegate connector handshake with vaulted credentials")
async def connectors_ping(
    slug: str,
    sess: DashboardSession,
    db: DbSession,
    body: PingBody | None = None,
) -> dict[str, Any]:
    """Loads vault row unless caller supplies ephemeral :class:`PingBody` secrets."""

    uid = _session_user_id(sess)
    envelope = await _resolve_envelope(body=body, db=db, uid=uid, slug=slug)
    klass = registry.resolve(slug)
    adapter = klass()
    ok = await adapter.ping(envelope)
    return {"slug": klass.slug, "ok": ok}


class InvokeProbeBody(BaseModel):
    """Lightweight outbound GET for connector egress validation."""

    url: AnyHttpUrl = Field(..., description="HTTPS origin to GET after vault auth headers apply.")
    connector_slug: str = Field(default="mcp_placeholder", description="Vault slug for Authorization header.")


@router.post("/invoke-probe", summary="GET an HTTPS URL using vaulted bearer headers + retry policy")
async def connectors_invoke_probe(
    probe: InvokeProbeBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    """Applies vaulted credentials to outbound probes (MCP prelude)."""

    uid = _session_user_id(sess)
    env = await vault_load_envelope(db, slug=probe.connector_slug.strip().lower(), user_id=uid)
    if env is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vault credential missing.")
    headers = env.bearer_header()
    url_txt = str(probe.url)

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:

        async def get_url() -> httpx.Response:
            rsp = await client.get(url_txt, headers=headers)
            rsp.raise_for_status()
            return rsp

        rsp = await retry_async_call(get_url)

    return {"status_code": rsp.status_code, "content_type": rsp.headers.get("content-type")}


class Phase3InstantiateBody(BaseModel):
    """Provision a Dynamic Connector row from a Phase 3 template manifest."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    template_id: str = Field(..., min_length=2, max_length=96)
    slug: str | None = Field(default=None, max_length=160)
    display_name: str | None = Field(default=None, max_length=256)
    secrets: DynamicConnectorSecretsInbound | None = None


class BallroomCalendarMemoBody(BaseModel):
    """Lightweight ballroom → calendar bridge (structured acceptance log only)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    session_id: str | None = Field(default=None, max_length=160)
    summary_markdown: str = Field(..., min_length=4, max_length=12_000)


@router.get("/phase3/templates", summary="List Phase 3 Communication & Knowledge templates")
async def phase3_templates_list(sess: DashboardSession) -> dict[str, Any]:
    """Return curated manifests sorted for cockpit consumption."""

    _ = sess
    templates = [phase3_template_public_dict(row) for row in iter_phase3_templates()]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for payload in templates:
        grouped.setdefault(str(payload["category"]), []).append(payload)
    return {"templates": templates, "grouped": grouped, "count": len(templates)}


@router.get("/phase3/integration-overview", summary="Phase 3 template alignment vs Dynamic Hub roster")
async def phase3_integration_overview(sess: DashboardSession, db: DbSession) -> dict[str, Any]:
    """Expose cockpit-ready mapping between curated templates and provisioned hub rows."""

    uid = _session_user_id(sess)
    svc = DynamicConnectorService()
    visible = await svc.list_visible(db, dashboard_user_id=uid)
    by_slug = {r.slug.strip().lower(): r for r in visible}
    cfg = get_settings()
    templates_block: list[dict[str, Any]] = []
    for tpl in iter_phase3_templates():
        slug_key = tpl.suggested_slug.strip().lower()
        hub = by_slug.get(slug_key)
        templates_block.append(
            {
                "template_id": tpl.template_id,
                "category": tpl.category,
                "title": tpl.title,
                "summary": tpl.summary,
                "suggested_slug": tpl.suggested_slug,
                "documentation_url": tpl.documentation_url,
                "auth_type": tpl.auth_type,
                "tool_count": len(tpl.tools),
                "suggested_manager_slugs": list(tpl.suggested_manager_slugs),
                "hub_row": hub.model_dump(mode="json") if hub else None,
            },
        )
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "dashboard_user_id": str(uid),
        "templates": templates_block,
        "obsidian": {
            "watch_enabled": cfg.phase3_obsidian_watch_enabled,
            "poll_interval_sec": cfg.phase3_obsidian_poll_interval_sec,
            "max_files_per_sync": cfg.phase3_obsidian_max_files_per_sync,
            "snapshot": obsidian_sync_snapshot(),
        },
        "cross_links": {
            "hive_mind": "/hive-mind",
            "external_projects": "/external-projects",
            "outputs": "/outputs",
            "ballroom": "/ballroom",
            "learning": "/learning",
        },
        "cost_governor_note": (
            "Dynamic MCP invokes call CostGovernor.assert_can_spend(session, delta_usd=0) so exhausted "
            "daily LLM budgets also pause outbound connector fan-out."
        ),
    }


@router.post(
    "/phase3/instantiate",
    summary="Create a Dynamic Connector row from a Phase 3 template",
)
async def phase3_instantiate_connector(
    body: Phase3InstantiateBody,
    sess: DashboardSession,
    db: DbSession,
) -> DynamicConnectorPublic:
    """Persist manifests + optional sealed secrets — inactive until upstream test passes."""

    uid = _session_user_id(sess)
    try:
        tpl = get_phase3_template(body.template_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    slug_txt = (body.slug or tpl.suggested_slug).strip().lower()
    display = body.display_name.strip() if body.display_name else tpl.title
    manifest = {"tools": [dict(tool) for tool in tpl.tools]}
    create = DynamicConnectorCreateBody(
        slug=slug_txt,
        display_name=display,
        base_url=tpl.base_url,
        auth_type=tpl.auth_type,
        allowed_manager_slugs=list(tpl.suggested_manager_slugs),
        mcp_manifest=manifest,
        secrets=body.secrets,
    )
    svc = DynamicConnectorService()
    try:
        return await svc.create_row(db, dashboard_user_id=uid, body=create)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/phase3/obsidian/status", summary="Obsidian vault → Chroma sync telemetry")
async def phase3_obsidian_status(sess: DashboardSession) -> dict[str, Any]:
    """Expose last poll statistics for dashboard operators."""

    _ = sess
    from app.core.config import get_settings

    cfg = get_settings()
    return {
        "enabled": cfg.phase3_obsidian_watch_enabled,
        "poll_interval_sec": cfg.phase3_obsidian_poll_interval_sec,
        "max_files_per_sync": cfg.phase3_obsidian_max_files_per_sync,
        "snapshot": obsidian_sync_snapshot(),
    }


@router.post("/phase3/obsidian/sync", summary="Force Obsidian vault embedding pass")
async def phase3_obsidian_sync_now(sess: DashboardSession) -> dict[str, Any]:
    """Run one embedding sweep immediately (still respects hive mind flags)."""

    _ = sess
    return await run_obsidian_vault_sync_once(force=True)


@router.post("/phase3/ballroom-calendar-memo", summary="Accept Ballroom meeting summaries for calendar follow-up")
async def phase3_ballroom_calendar_memo(
    body: BallroomCalendarMemoBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    """Structured ingest hook — returns routing hints when ``google_calendar`` hub rows exist."""

    uid = _session_user_id(sess)
    svc = DynamicConnectorService()
    cal_slug = "google_calendar"
    cal_row = await svc.fetch_by_slug(db, slug=cal_slug)
    calendar_hints = {
        "recommended_slug": cal_slug,
        "hub_row_present": cal_row is not None,
        "hub_row_active": bool(cal_row and cal_row.is_active),
        "suggested_tools": ["events_list", "events_insert", "freebusy_query", "events_patch"],
        "memo_chars": len(body.summary_markdown),
    }
    logger.info(
        "phase3.ballroom_calendar.memo",
        agent_id=str(uid),
        swarm_id=body.session_id or "unknown-session",
        task_id="ballroom-calendar-memo",
        summary_chars=len(body.summary_markdown),
    )
    return {"ok": True, "accepted": True, "calendar_hints": calendar_hints}


__all__ = ["router"]
