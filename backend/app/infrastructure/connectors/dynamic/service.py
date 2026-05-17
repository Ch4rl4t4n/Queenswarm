"""Postgres-backed CRUD plus sealed secret handling for the Dynamic Connector Hub."""

from __future__ import annotations

import json
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from cryptography.fernet import InvalidToken
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cost_governor import BudgetExceededError, CostGovernor
from app.infrastructure.connectors.dynamic.hub import DynamicConnectorHub, invalidate_registry_cache, manifest_tool_default
from app.infrastructure.connectors.phase3.catalog import phase3_catalog_addon_lines
from app.infrastructure.connectors.dynamic.schemas import (
    DynamicConnectorCreateBody,
    DynamicConnectorPatchBody,
    DynamicConnectorPublic,
)
from app.infrastructure.connectors.secure_vault import seal_dynamic_connector_blob, unseal_dynamic_connector_blob
from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.dynamic_connector import DynamicConnector

logger = get_logger(__name__)

_MANAGER_PERMISSION_SCOPES: dict[str, frozenset[str]] = {
    "research_intelligence": frozenset({"tool:read", "tool:search", "tool:web"}),
    "content_creation": frozenset({"tool:read", "tool:web"}),
    "execution_operations": frozenset({"tool:read", "tool:search", "tool:web", "tool:write", "tool:execute"}),
    "review_quality": frozenset({"tool:read", "tool:search"}),
    "personal_life": frozenset({"tool:read"}),
    "optimization": frozenset({"tool:read", "tool:search"}),
}


def manifest_unused_query_params(path_tpl: str, arguments: dict[str, Any]) -> dict[str, str]:
    """Expose manifest arguments absent from ``{placeholder}`` segments as HTTP query pairs."""

    keys = set(re.findall(r"\{(\w+)\}", path_tpl))
    params: dict[str, str] = {}
    for raw_key, raw_val in arguments.items():
        key_txt = str(raw_key)
        if key_txt in keys:
            continue
        if isinstance(raw_val, (dict, list)):
            continue
        params[key_txt] = str(raw_val)
    return params


def _public_model(row: DynamicConnector) -> DynamicConnectorPublic:
    tested_at = row.last_tested_at
    tested_txt = tested_at.isoformat() if isinstance(tested_at, datetime) else None
    mgrs: list[str] = []
    raw_mgr = row.allowed_manager_slugs
    if isinstance(raw_mgr, list):
        mgrs = [str(m).strip().lower() for m in raw_mgr if str(m).strip()]

    bk = row.builtin_kind
    builtin_kind_trim = bk.strip() if isinstance(bk, str) else bk

    return DynamicConnectorPublic(
        id=str(row.id),
        slug=row.slug,
        display_name=row.display_name,
        base_url=row.base_url,
        auth_type=row.auth_type,
        mcp_manifest=dict(row.mcp_manifest) if isinstance(row.mcp_manifest, dict) else None,
        allowed_manager_slugs=mgrs,
        is_active=bool(row.is_active),
        is_builtin=bool(row.is_builtin),
        builtin_kind=builtin_kind_trim,
        last_tested_at=tested_txt,
    )


def _secrets_to_headers(auth_type: str, payload: dict[str, Any]) -> dict[str, str]:
    """Map decrypted JSON bundle into outbound HTTP headers (never logged)."""

    style = auth_type.strip().lower()
    headers: dict[str, str] = {}
    if style in {"", "none"}:
        return headers
    if style == "api_key":
        key = payload.get("api_key")
        hk = str(payload.get("api_key_header_name") or "X-API-KEY").strip() or "X-API-KEY"
        if isinstance(key, str) and key.strip():
            headers[hk] = key.strip()
        return headers
    if style == "bearer_token":
        tok = payload.get("bearer_token")
        if isinstance(tok, str) and tok.strip():
            headers["Authorization"] = f"Bearer {tok.strip()}"
        return headers
    if style == "oauth2":
        tok = payload.get("oauth2_access_token")
        if isinstance(tok, str) and tok.strip():
            headers["Authorization"] = f"Bearer {tok.strip()}"
        return headers
    return headers


async def merged_static_and_dynamic_allowlist(session: AsyncSession, *, manager_template_slug: str) -> tuple[str, ...]:
    """Union static MANAGER_REGISTRY allowlisted slugs plus active dynamic MCP rows."""

    from app.domain.agents.managers.registry import get_manager_template

    snaps = await DynamicConnectorHub.snapshots(session)
    dyn = DynamicConnectorHub.slugs_available_for_manager(snaps, manager_slug=manager_template_slug)
    static_specs = tuple(get_manager_template(manager_template_slug).connector_allowlist)
    merged = sorted({s.strip().lower() for s in static_specs}.union(set(dyn)))
    return tuple(merged)


async def describe_connector_catalog_addon(session: AsyncSession) -> str:
    """Append dynamic MCP summaries for orchestrator template picking."""

    rows = await DynamicConnectorHub.snapshots(session)
    lines = ["### Dynamic MCP connectors (PostgreSQL manifests)"]
    for row in rows:
        mgr_note = ",".join(row.allowed_manager_slugs) if row.allowed_manager_slugs else "*"
        lines.append(f"- `{row.slug}` ({row.display_name}) managers=[{mgr_note}] builtin={row.is_builtin}")
    lines.extend(phase3_catalog_addon_lines())
    return "\n".join(lines)


class DynamicConnectorService:
    """Request-scoped service helpers for FastAPI routers + Ballroom."""

    async def list_visible(self, session: AsyncSession, *, dashboard_user_id: uuid.UUID | None) -> list[DynamicConnectorPublic]:
        """Return builtins plus rows owned by the operator (JWT subject)."""

        b_stmt = select(DynamicConnector).where(DynamicConnector.is_builtin.is_(True)).order_by(DynamicConnector.slug.asc())
        builtins = tuple((await session.scalars(b_stmt)).all())

        owned: tuple[DynamicConnector, ...] = ()
        if dashboard_user_id is not None:
            own_stmt = select(DynamicConnector).where(
                DynamicConnector.dashboard_user_id == dashboard_user_id,
            ).order_by(DynamicConnector.slug.asc())
            owned = tuple((await session.scalars(own_stmt)).all())

        seen: dict[str, DynamicConnector] = {b.slug.lower(): b for b in builtins}
        for chunk in owned:
            seen.setdefault(chunk.slug.lower(), chunk)
        ordered = sorted(seen.values(), key=lambda row: row.slug.lower())
        return [_public_model(row) for row in ordered]

    async def fetch_by_slug(self, session: AsyncSession, *, slug: str) -> DynamicConnector | None:
        """Return ORM row for slug if present."""

        cleaned = slug.strip().lower()
        stmt = select(DynamicConnector).where(func.lower(DynamicConnector.slug) == cleaned).limit(1)
        return await session.scalar(stmt)

    async def create_row(
        self,
        session: AsyncSession,
        *,
        dashboard_user_id: uuid.UUID,
        body: DynamicConnectorCreateBody,
    ) -> DynamicConnectorPublic:
        """Persist a new sealed connector row."""

        if body.slug.strip().lower() == "grokipedia":
            msg = "slug grokipedia is reserved for the built-in Grokipedia scraper."
            raise ValueError(msg)

        cipher: str | None = None
        if body.auth_type not in {"", "none"}:
            secrets_model = body.secrets or None
            if secrets_model is None:
                msg = "secrets payload required whenever auth_type is not none."
                raise ValueError(msg)
            cipher = seal_dynamic_connector_blob(secrets_model.to_sealed_payload())

        manifest = dict(body.mcp_manifest) if isinstance(body.mcp_manifest, dict) else manifest_tool_default()
        mgrs_raw = tuple({m.strip().lower() for m in body.allowed_manager_slugs if m.strip()})

        row = DynamicConnector(
            slug=body.slug.strip().lower(),
            display_name=body.display_name.strip(),
            base_url=str(body.base_url) if body.base_url is not None else None,
            auth_type=body.auth_type,
            secrets_cipher=cipher,
            mcp_manifest=manifest,
            allowed_manager_slugs=list(mgrs_raw),
            is_active=False,
            is_builtin=False,
            builtin_kind=None,
            last_tested_at=None,
            dashboard_user_id=dashboard_user_id,
        )
        session.add(row)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ValueError("slug already registered") from exc

        await session.refresh(row)
        await invalidate_registry_cache()
        logger.info(
            "dynamic_hub.connector_created",
            agent_id=str(dashboard_user_id),
            swarm_id=row.slug,
            task_id="connector-create",
        )
        return _public_model(row)

    async def patch_row(
        self,
        session: AsyncSession,
        *,
        connector_id: uuid.UUID,
        dashboard_user_id: uuid.UUID,
        body: DynamicConnectorPatchBody,
    ) -> DynamicConnectorPublic:
        """Bounded updates with optional ciphertext rotation."""

        row = await session.get(DynamicConnector, connector_id)
        if row is None:
            raise ValueError("connector missing")
        if row.is_builtin:
            raise ValueError("built-in connectors are immutable via API")
        if row.dashboard_user_id != dashboard_user_id:
            raise ValueError("ownership mismatch")

        if body.display_name is not None:
            row.display_name = body.display_name.strip()
        if body.base_url is not None:
            row.base_url = str(body.base_url)
        if body.auth_type is not None:
            row.auth_type = body.auth_type
        if body.allowed_manager_slugs is not None:
            mgrs_raw = tuple({m.strip().lower() for m in body.allowed_manager_slugs if m.strip()})
            row.allowed_manager_slugs = list(mgrs_raw)
        if body.mcp_manifest is not None:
            row.mcp_manifest = dict(body.mcp_manifest)
        if body.is_active is not None:
            row.is_active = body.is_active
        if body.secrets is not None:
            blob = seal_dynamic_connector_blob(body.secrets.to_sealed_payload())
            row.secrets_cipher = blob

        await session.commit()
        await session.refresh(row)
        await invalidate_registry_cache()
        logger.info(
            "dynamic_hub.connector_updated",
            agent_id=str(dashboard_user_id),
            swarm_id=row.slug,
            task_id="connector-patch",
        )
        return _public_model(row)

    async def delete_row(
        self,
        session: AsyncSession,
        *,
        connector_id: uuid.UUID,
        dashboard_user_id: uuid.UUID,
    ) -> None:
        """Remove operator-owned connectors."""

        row = await session.get(DynamicConnector, connector_id)
        if row is None:
            return
        if row.is_builtin:
            raise ValueError("cannot delete builtin connector")
        if row.dashboard_user_id != dashboard_user_id:
            raise ValueError("ownership mismatch")
        await session.delete(row)
        await session.commit()
        await invalidate_registry_cache()
        logger.info(
            "dynamic_hub.connector_deleted",
            agent_id=str(dashboard_user_id),
            swarm_id=row.slug,
            task_id="connector-delete",
        )

    def _secrets_dict(self, row: DynamicConnector) -> dict[str, Any]:
        """Decrypt ciphertext or return `{}` — never propagate outside callers."""

        raw = row.secrets_cipher
        if not isinstance(raw, str) or not raw.strip():
            return {}
        try:
            return unseal_dynamic_connector_blob(raw)
        except (InvalidToken, ValueError, TypeError):
            logger.warning(
                "dynamic_hub.secret_decrypt_failed",
                agent_id=str(row.dashboard_user_id or "builtin"),
                swarm_id=row.slug,
                task_id="cipher",
            )
            return {}

    async def test_upstream(
        self,
        session: AsyncSession,
        *,
        connector_id: uuid.UUID,
        dashboard_user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Cheap HEAD-or-GET smoke test activating connector after success."""

        row = await session.get(DynamicConnector, connector_id)
        if row is None:
            raise ValueError("connector missing")
        if not row.is_builtin:
            if row.dashboard_user_id != dashboard_user_id:
                raise ValueError("ownership mismatch")
        cfg = get_settings()

        throttle = await DynamicConnectorHub.throttle_ok(row.slug)
        if not throttle:
            return {"slug": row.slug, "ok": False, "reason": "rate_limited_local"}

        if await DynamicConnectorHub.breaker_is_open(row.slug):
            return {"slug": row.slug, "ok": False, "reason": "circuit_open"}

        base = (row.base_url or "").strip()
        settings_override = (cfg.grokipedia_base_url or "").strip()
        if isinstance(row.builtin_kind, str) and row.builtin_kind.lower() == "grokipedia" and settings_override:
            base = settings_override.rstrip("/")

        if not base:
            return {"slug": row.slug, "ok": False, "reason": "missing_base_url"}

        headers = dict(_secrets_to_headers(row.auth_type, self._secrets_dict(row)))

        timeout = httpx.Timeout(cfg.dynamic_connector_tool_timeout_ms / 1000.0)
        ok = False
        status_payload: dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                rsp = await client.head(base, headers=dict(headers))
                if rsp.status_code >= 400 or rsp.status_code == 405:
                    rsp_get = await client.get(base, headers=dict(headers))
                    ok = rsp_get.status_code < 400
                    status_payload = {"status_code": rsp_get.status_code}
                else:
                    ok = rsp.status_code < 400
                    status_payload = {"status_code": rsp.status_code}
                if ok:
                    await DynamicConnectorHub.breaker_note_success(row.slug)
                else:
                    await DynamicConnectorHub.breaker_note_failure(row.slug)
            except httpx.HTTPError as exc:
                await DynamicConnectorHub.breaker_note_failure(row.slug)
                status_payload = {"error_kind": exc.__class__.__name__}

        now = datetime.now(tz=UTC)
        row.last_tested_at = now
        if ok and not row.is_builtin:
            row.is_active = True
        elif ok and row.is_builtin:
            row.is_active = True
        await session.commit()

        logger.info(
            "dynamic_hub.test_complete",
            agent_id=str(dashboard_user_id),
            swarm_id=row.slug,
            task_id="connector-test",
            outcome="ok" if ok else "fail",
        )

        await invalidate_registry_cache()
        resp = {"slug": row.slug, "ok": bool(ok)}
        resp.update(status_payload)
        return resp


async def invoke_dynamic_tool(
    session: AsyncSession,
    *,
    connector_slug: str,
    tool_name: str,
    arguments: dict[str, Any],
    manager_slug: str | None = None,
    agent_task_id: str = "executor",
    granted_permissions: frozenset[str] | None = None,
) -> str:
    """Execute manifest-defined HTTP MCP tool with hardened budgets."""

    settings = get_settings()
    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=connector_slug.strip().lower())
    if row is None or not row.is_active:
        return f"dynamic_invoke_error: connector `{connector_slug}` inactive or unknown"

    gov = CostGovernor()
    try:
        await gov.assert_can_spend(session, delta_usd=0.0)
    except BudgetExceededError:
        logger.warning(
            "dynamic_hub.invoke_budget_block",
            agent_id=str(row.dashboard_user_id or "hive"),
            swarm_id=row.slug,
            task_id=agent_task_id,
        )
        return "dynamic_invoke_error: cost_governor_daily_budget_exceeded"

    if manager_slug:
        snaps = await DynamicConnectorHub.snapshots(session)
        mgr_allowed = DynamicConnectorHub.slugs_available_for_manager(
            snaps,
            manager_slug=manager_slug.strip().lower(),
        )
        if connector_slug.strip().lower() not in mgr_allowed:
            return f"dynamic_invoke_error: `{connector_slug}` not allowlisted for manager `{manager_slug}`"

    throttle = await DynamicConnectorHub.throttle_ok(row.slug)
    if not throttle:
        return "dynamic_invoke_error: rate_limited(Postgres-backed sliding window)"

    if await DynamicConnectorHub.breaker_is_open(row.slug):
        return "dynamic_invoke_error: circuit_open(Postgres/Redis)"

    manifest = dict(row.mcp_manifest) if isinstance(row.mcp_manifest, dict) else manifest_tool_default()
    tools_blob = manifest.get("tools") or []
    cfg_tool: dict[str, Any] | None = None
    if isinstance(tools_blob, list):
        for ent in tools_blob:
            if not isinstance(ent, dict):
                continue
            nm = str(ent.get("name") or "").strip()
            if nm == tool_name.strip():
                cfg_tool = ent
                break
    if cfg_tool is None:
        return f"dynamic_invoke_error: tool `{tool_name}` missing from manifest"

    normalized_manager = (manager_slug or "").strip().lower()
    tool_manager_filters = cfg_tool.get("allowed_manager_slugs")
    if isinstance(tool_manager_filters, list):
        allowed_tool_managers = {
            str(item).strip().lower()
            for item in tool_manager_filters
            if str(item).strip()
        }
        if allowed_tool_managers and (not normalized_manager or normalized_manager not in allowed_tool_managers):
            return f"dynamic_invoke_error: tool `{tool_name}` blocked for manager `{normalized_manager or 'unknown'}`"

    required_permission = str(cfg_tool.get("required_permission") or "").strip().lower()
    resolved_permissions = set(granted_permissions or ())
    if not resolved_permissions and normalized_manager:
        resolved_permissions = set(_MANAGER_PERMISSION_SCOPES.get(normalized_manager, frozenset({"tool:read"})))
    if required_permission and required_permission not in resolved_permissions:
        return f"dynamic_invoke_error: missing_permission({required_permission})"

    per_tool_limit = cfg_tool.get("rate_limit_per_minute")
    tool_limit = int(per_tool_limit) if isinstance(per_tool_limit, int) else None
    if not await DynamicConnectorHub.throttle_tool_ok(row.slug, tool_name, limit_per_minute=tool_limit):
        return "dynamic_invoke_error: tool_rate_limited"

    path_tpl = str(cfg_tool.get("path") or "/")
    meth = str(cfg_tool.get("method") or "GET").upper()

    substitutions = {str(k): str(v) for k, v in arguments.items()}
    substituted = path_tpl
    for placeholder, value_txt in substitutions.items():
        substituted = substituted.replace(f"{{{placeholder}}}", value_txt)

    base_txt = (row.base_url or "").strip()
    if isinstance(row.builtin_kind, str) and row.builtin_kind.lower() == "grokipedia" and settings.grokipedia_base_url.strip():
        base_txt = settings.grokipedia_base_url.strip().rstrip("/")

    if not base_txt:
        return "dynamic_invoke_error: connector base_url missing"

    resolved_path = substituted if substituted.startswith("/") else f"/{substituted}"
    endpoint = urljoin(base_txt.rstrip("/") + "/", resolved_path.lstrip("/"))

    headers = dict(_secrets_to_headers(row.auth_type, svc._secrets_dict(row)))  # noqa: SLF001
    extra_hdr = cfg_tool.get("headers")
    if isinstance(extra_hdr, dict):
        for hk, hv in extra_hdr.items():
            headers[str(hk)] = str(hv)

    timeout = httpx.Timeout(settings.dynamic_connector_tool_timeout_ms / 1000.0)
    trace_hint = uuid.uuid4().hex

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        started = time.perf_counter()
        try:
            if meth in {"GET", "HEAD"}:
                query_params = manifest_unused_query_params(path_tpl, arguments)
                rsp = await client.request(
                    meth,
                    endpoint,
                    headers=dict(headers),
                    params=query_params or None,
                )
            else:
                rsp = await client.request(meth, endpoint, headers=dict(headers), json=arguments)
            duration_ms = (time.perf_counter() - started) * 1000.0

            snippet = rsp.text.strip()[:4000]
            if rsp.status_code >= 400:
                await DynamicConnectorHub.breaker_note_failure(row.slug)
                await DynamicConnectorHub.record_tool_invocation(
                    row.slug,
                    tool_name,
                    success=False,
                    latency_ms=duration_ms,
                )
                return f"dynamic_invoke_http_{rsp.status_code}: {snippet[:800]}"
            await DynamicConnectorHub.breaker_note_success(row.slug)
            await DynamicConnectorHub.record_tool_invocation(
                row.slug,
                tool_name,
                success=True,
                latency_ms=duration_ms,
            )

            logger.info(
                "dynamic_hub.tool_success",
                agent_id=str(row.dashboard_user_id or "hive"),
                swarm_id=row.slug,
                task_id=agent_task_id,
                latency_ms=float(f"{duration_ms:.2f}"),
                trace_hint=trace_hint[:8],
            )
            return snippet or "(empty body)"
        except httpx.HTTPError as exc:
            await DynamicConnectorHub.breaker_note_failure(row.slug)
            await DynamicConnectorHub.record_tool_invocation(row.slug, tool_name, success=False, latency_ms=None)
            logger.warning(
                "dynamic_hub.tool_failed",
                agent_id=str(row.dashboard_user_id or "hive"),
                swarm_id=row.slug,
                task_id=agent_task_id,
                trace_hint=trace_hint[:8],
                error=exc.__class__.__name__,
            )
            return f"dynamic_invoke_error: {exc.__class__.__name__}"


__all__ = [
    "DynamicConnectorService",
    "describe_connector_catalog_addon",
    "invoke_dynamic_tool",
    "manifest_unused_query_params",
    "merged_static_and_dynamic_allowlist",
]
