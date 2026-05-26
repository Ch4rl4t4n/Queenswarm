"""External integration registry — keys, permissions, routing, and audit persistence."""

from __future__ import annotations

import json
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.domain.external.hive_audit import mirror_external_audit_to_vault
from app.domain.external.managers.food_ordering_manager import FoodOrderingManager
from app.domain.external.managers.generic_project_manager import GenericProjectManager
from app.domain.external.managers.trading_manager import TradingManager
from app.infrastructure.persistence.models.external_project import ExternalProject, ExternalProjectApiKey, ExternalProjectRunAudit
from app.application.services.dashboard_crypto import hash_dashboard_password, verify_dashboard_password

PERM_RUN = "run"
PERM_MCP_CALL = "mcp:call"
PERM_TRADING_LIVE = "trading:live"

EXTERNAL_KEY_PREFIX = "qs_ep_"
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{1,126}$")


def normalize_external_slug(raw: str) -> str:
    """Lowercase slug with hive-safe charset."""

    s = raw.strip().lower()
    if not _SLUG_RE.fullmatch(s):
        msg = (
            "project_slug must start with a letter, use lowercase alphanumeric plus _ or -, "
            "length 2-127."
        )
        raise ValueError(msg)
    if s in {"results", "projects"}:
        msg = f"Reserved external slug: {s!r}."
        raise ValueError(msg)
    return s


def build_plaintext_external_key(key_id: uuid.UUID) -> str:
    """Mint an opaque secret shown exactly once to operators."""

    return f"{EXTERNAL_KEY_PREFIX}{key_id.hex}.{secrets.token_urlsafe(40)}"


def parse_external_api_key(raw: str) -> tuple[uuid.UUID, str] | None:
    """Split ``qs_ep_<uuid>.<secret>`` payloads."""

    trimmed = raw.strip()
    if not trimmed.startswith(EXTERNAL_KEY_PREFIX):
        return None
    rest = trimmed[len(EXTERNAL_KEY_PREFIX) :]
    dot = rest.find(".")
    if dot < 0:
        return None
    hex_part = rest[:dot]
    suffix = rest[dot + 1 :]
    if len(hex_part) != 32 or len(suffix) < 16:
        return None
    try:
        parsed_id = uuid.UUID(hex=hex_part)
    except ValueError:
        return None
    return parsed_id, suffix


def permission_allowed(rows: list[str] | None, required: str) -> bool:
    """Match permissive scopes (`*` always grants)."""

    if not rows:
        return False
    scopes = {str(x).strip() for x in rows if str(x).strip()}
    if "*" in scopes:
        return True
    return required in scopes


def estimate_run_cost_usd(action: str, project_kind: str) -> Decimal:
    """Cheap heuristic cost telemetry for dashboards — swap with ledger coupling later."""

    base = Decimal("0.0005")
    pk = project_kind.strip().lower()
    act = action.lower()
    if pk == "trading" and "execute" in act:
        return Decimal("0.025") + base
    if pk == "food_ordering" and "submit" in act:
        return Decimal("0.012") + base
    return base


def _payload_excerpt(payload: dict[str, Any], cap: int) -> str:
    """Truncate JSON previews for Postgres TEXT."""

    try:
        dumped = json.dumps(payload, sort_keys=True, default=str)
    except (TypeError, ValueError):
        dumped = str(payload)
    if len(dumped) <= cap:
        return dumped
    return dumped[: cap - 1] + "…"


@dataclass(slots=True)
class ResolvedInvocation:
    """Structured routing outcome consumed by HTTP/MCP gateways."""

    result: dict[str, Any]
    ok: bool
    human_approval_required: bool
    human_approved: bool | None


async def resolve_external_principal(
    session: AsyncSession,
    *,
    raw_key: str,
) -> tuple[ExternalProject, ExternalProjectApiKey] | None:
    """Resolve API secrets against bcrypt hashes."""

    parsed = parse_external_api_key(raw_key)
    if parsed is None:
        return None
    key_id, plaintext = parsed
    stmt_key = select(ExternalProjectApiKey).where(ExternalProjectApiKey.id == key_id)
    api_row = (await session.execute(stmt_key)).scalar_one_or_none()
    if api_row is None or api_row.revoked_at is not None:
        return None
    if not verify_dashboard_password(plaintext, api_row.secret_hash):
        return None

    stmt_proj = select(ExternalProject).where(
        ExternalProject.id == api_row.project_id,
        ExternalProject.is_active.is_(True),
    )
    proj_row = (await session.execute(stmt_proj)).scalar_one_or_none()
    if proj_row is None:
        return None

    await session.execute(
        update(ExternalProjectApiKey)
        .where(ExternalProjectApiKey.id == api_row.id)
        .values(last_used_at=datetime.now(tz=UTC)),
    )
    await session.commit()
    return proj_row, api_row


async def route_external_invocation(
    session: AsyncSession,
    *,
    project: ExternalProject,
    api_key: ExternalProjectApiKey | None,
    action: str,
    payload: dict[str, Any],
    channel: str,
    settings: Settings | None = None,
) -> ResolvedInvocation:
    """Dispatch manager lanes after validating scopes."""

    cfg = settings or get_settings()
    perms_raw = api_key.permissions if api_key is not None else []
    perms_list = list(perms_raw) if isinstance(perms_raw, list) else []

    need = PERM_MCP_CALL if channel == "mcp" else PERM_RUN
    if not permission_allowed(perms_list, need):
        return ResolvedInvocation(
            result={"status": "blocked", "reason": "forbidden", "detail": f"missing scope {need}"},
            ok=False,
            human_approval_required=False,
            human_approved=None,
        )

    proj_kind = project.project_kind.strip().lower()
    proj_settings = dict(project.settings or {})

    try:
        if proj_kind == "trading":
            mgr = TradingManager()
            if (
                action == "execute_trade"
                and str(proj_settings.get("trading_mode") or "paper").lower() == "real"
                and not permission_allowed(perms_list, PERM_TRADING_LIVE)
            ):
                return ResolvedInvocation(
                    result={
                        "status": "blocked",
                        "reason": "forbidden",
                        "detail": f"missing scope {PERM_TRADING_LIVE} for live trading",
                    },
                    ok=False,
                    human_approval_required=False,
                    human_approved=None,
                )
            out = await mgr.handle(action=action, payload=payload, project_settings=proj_settings)
            venue = str(proj_settings.get("venue") or "").strip().lower()
            if (
                out.get("status") == "queued_for_execution"
                and venue in {"polymarket", "kalshi"}
            ):
                from app.application.services.prediction_market_trading import execute_live_prediction_trade

                live_out = await execute_live_prediction_trade(
                    session,
                    project=project,
                    payload=payload,
                    project_settings=proj_settings,
                )
                out = {**out, **live_out}
        elif proj_kind == "food_ordering":
            out = await FoodOrderingManager().handle(
                action=action,
                payload=payload,
                project_settings=proj_settings,
            )
        elif proj_kind == "generic":
            out = await GenericProjectManager().handle(
                action=action,
                payload=payload,
                project_settings=proj_settings,
            )
        else:
            msg = f"Unknown project_kind {proj_kind!r}"
            raise ValueError(msg)
    except ValueError as exc:
        return ResolvedInvocation(
            result={"status": "error", "detail": str(exc)},
            ok=False,
            human_approval_required=False,
            human_approved=None,
        )

    approval_needed = out.get("reason") == "human_approval_required"
    ok_flag = bool(out.get("status") not in {"blocked", "error"}) and not approval_needed
    human_ok = None
    if approval_needed:
        ok_flag = False
    elif out.get("status") == "queued_for_execution":
        human_ok = bool(payload.get("human_approval_confirmed"))
    elif out.get("status") == "executed":
        ok_flag = bool(out.get("verified"))
        human_ok = bool(payload.get("human_approval_confirmed"))

    return ResolvedInvocation(
        result=out,
        ok=ok_flag,
        human_approval_required=approval_needed,
        human_approved=human_ok,
    )


async def persist_run_audit(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    api_key_id: uuid.UUID | None,
    action_slug: str,
    ok: bool,
    latency_ms: int,
    cost_usd: Decimal,
    human_approval_required: bool,
    human_approved: bool | None,
    payload: dict[str, Any],
    result_summary: dict[str, Any],
    excerpt_cap: int = 6000,
) -> uuid.UUID:
    """Insert immutable audit rows used by dashboards + Hive mirrors."""

    row = ExternalProjectRunAudit(
        id=uuid.uuid4(),
        project_id=project_id,
        api_key_id=api_key_id,
        action_slug=action_slug,
        ok=ok,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        human_approval_required=human_approval_required,
        human_approved=human_approved,
        payload_excerpt=_payload_excerpt(payload, excerpt_cap),
        result_summary=result_summary,
    )
    session.add(row)
    await session.commit()
    return row.id


async def emit_external_audit_trail(
    *,
    project_slug: str,
    action_slug: str,
    ok: bool,
    latency_ms: int,
    audit_id: uuid.UUID,
    summary: dict[str, Any],
    api_key_id: uuid.UUID | None,
    settings: Settings | None = None,
) -> None:
    """Forward summarized payloads into Hive vault Markdown stitching."""

    agent_anchor = f"external:{api_key_id}" if api_key_id else "external:anonymous"
    await mirror_external_audit_to_vault(
        project_slug=project_slug,
        action_slug=action_slug,
        ok=ok,
        latency_ms=latency_ms,
        summary=summary,
        agent_id=agent_anchor,
        swarm_id=project_slug,
        task_id=str(audit_id),
        settings=settings,
    )


async def load_project_for_slug_owner(
    session: AsyncSession,
    *,
    slug: str,
    owner_dashboard_user_id: uuid.UUID,
) -> ExternalProject | None:
    """Return dashboard scoped rows."""

    stmt = (
        select(ExternalProject)
        .where(
            ExternalProject.slug == slug,
            ExternalProject.owner_dashboard_user_id == owner_dashboard_user_id,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_projects_for_owner(session: AsyncSession, *, owner_id: uuid.UUID) -> list[ExternalProject]:
    """Enumerate cockpit-visible integrations."""

    stmt = (
        select(ExternalProject)
        .where(ExternalProject.owner_dashboard_user_id == owner_id)
        .order_by(ExternalProject.created_at.desc())
    )
    rows = await session.execute(stmt)
    return list(rows.scalars().all())


async def create_external_project_row(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    slug: str,
    display_name: str,
    project_kind: str,
    settings_blob: dict[str, Any],
    webhook_url: str | None,
    webhook_plain_secret: str | None,
) -> ExternalProject:
    """Persist a registry row with optional webhook digest."""

    normalized_slug = normalize_external_slug(slug)
    webhook_hash = hash_dashboard_password(webhook_plain_secret) if webhook_plain_secret else None
    row = ExternalProject(
        id=uuid.uuid4(),
        slug=normalized_slug,
        display_name=display_name.strip()[:256],
        project_kind=project_kind.strip().lower()[:32],
        owner_dashboard_user_id=owner_id,
        settings=settings_blob,
        webhook_url=webhook_url.strip() if webhook_url else None,
        webhook_secret_hash=webhook_hash,
        is_active=True,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(row)
    return row


async def mint_external_api_key(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    label: str | None,
    permissions: list[str],
) -> tuple[uuid.UUID, str]:
    """Return plaintext credential once alongside persisted bcrypt digest."""

    key_id = uuid.uuid4()
    plaintext = build_plaintext_external_key(key_id)
    digest = hash_dashboard_password(plaintext)
    row = ExternalProjectApiKey(
        id=key_id,
        project_id=project_id,
        label=(label.strip()[:160] if label else None),
        secret_hash=digest,
        permissions=permissions,
    )
    session.add(row)
    await session.commit()
    return key_id, plaintext


async def aggregate_metrics(session: AsyncSession, *, project_id: uuid.UUID) -> dict[str, Any]:
    """Roll inexpensive aggregates for dashboard charts."""

    total_stmt = select(func.count()).select_from(ExternalProjectRunAudit).where(
        ExternalProjectRunAudit.project_id == project_id,
    )
    ok_stmt = select(func.count()).select_from(ExternalProjectRunAudit).where(
        ExternalProjectRunAudit.project_id == project_id,
        ExternalProjectRunAudit.ok.is_(True),
    )
    cost_stmt = select(func.coalesce(func.sum(ExternalProjectRunAudit.cost_usd), 0)).where(
        ExternalProjectRunAudit.project_id == project_id,
    )
    total = int((await session.execute(total_stmt)).scalar_one())
    successes = int((await session.execute(ok_stmt)).scalar_one())
    cost = await session.execute(cost_stmt)
    cost_total = cost.scalar_one()
    rate = float(successes) / float(total) if total else 0.0
    return {
        "runs_total": total,
        "runs_success": successes,
        "success_rate": rate,
        "cost_usd_total": float(cost_total or 0),
    }


async def recent_run_series(session: AsyncSession, *, project_id: uuid.UUID, limit: int = 48) -> list[dict[str, Any]]:
    """Return chronological telemetry buckets."""

    stmt = (
        select(ExternalProjectRunAudit)
        .where(ExternalProjectRunAudit.project_id == project_id)
        .order_by(ExternalProjectRunAudit.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    series: list[dict[str, Any]] = []
    for row in reversed(rows):
        series.append(
            {
                "t": row.created_at.isoformat(),
                "ok": row.ok,
                "latency_ms": row.latency_ms,
                "cost_usd": float(row.cost_usd or 0),
                "action": row.action_slug,
            },
        )
    return series


__all__ = [
    "EXTERNAL_KEY_PREFIX",
    "PERM_MCP_CALL",
    "PERM_RUN",
    "PERM_TRADING_LIVE",
    "ResolvedInvocation",
    "estimate_run_cost_usd",
    "aggregate_metrics",
    "build_plaintext_external_key",
    "create_external_project_row",
    "emit_external_audit_trail",
    "list_projects_for_owner",
    "load_project_for_slug_owner",
    "mint_external_api_key",
    "normalize_external_slug",
    "parse_external_api_key",
    "permission_allowed",
    "persist_run_audit",
    "recent_run_series",
    "resolve_external_principal",
    "route_external_invocation",
]
