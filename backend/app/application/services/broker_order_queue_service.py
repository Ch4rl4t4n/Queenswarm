"""Track P RA5 — HITL broker order queue (propose → approve → MCP execute)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

BROKER_ORDER_QUEUE_SETTINGS_KEY = "broker_order_queue"
MAX_ORDERS_STORED = 80
MAX_PENDING = 30

BrokerOrderStatus = Literal["pending", "approved", "rejected", "executed", "failed"]
BrokerOrderDecision = Literal["approve", "reject"]


class BrokerOrderProposeIn(BaseModel):
    """Agent or operator proposal for a live broker order."""

    model_config = ConfigDict(extra="forbid")

    venue: str = "polymarket"
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(default="", max_length=2000)
    notional_usd: float = Field(default=0.0, ge=0.0, le=100_000.0)
    payload: dict[str, Any] = Field(default_factory=dict)
    project_settings: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    proposed_by: str | None = None


class BrokerOrderItemOut(BaseModel):
    """One row in the broker HITL order queue."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: BrokerOrderStatus
    venue: str
    title: str
    detail: str
    notional_usd: float
    payload: dict[str, Any] = Field(default_factory=dict)
    project_settings: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    proposed_by: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    review_note: str = ""
    execution_status: str | None = None
    execution_detail: str | None = None
    workspace_href: str = "/apps-tools/trading-automation?section=orders#broker-order-queue"


class BrokerOrderQueueSnapshotOut(BaseModel):
    """Trading Automation order queue snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    pending_count: int = 0
    executed_count: int = 0
    rejected_count: int = 0
    items: list[BrokerOrderItemOut] = Field(default_factory=list)
    operator_hint: str = ""
    workspace_href: str = "/apps-tools/trading-automation?section=orders#broker-order-queue"


class BrokerOrderReviewIn(BaseModel):
    """Approve or reject a pending broker order."""

    model_config = ConfigDict(extra="forbid")

    decision: BrokerOrderDecision
    note: str = Field(default="", max_length=500)


class BrokerOrderReviewOut(BaseModel):
    """Review action result."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: BrokerOrderStatus
    execution_status: str | None = None
    execution_detail: str | None = None
    reviewed_at: datetime


def _queue_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(BROKER_ORDER_QUEUE_SETTINGS_KEY)
    if not isinstance(bucket, dict):
        return {"orders": []}
    orders = bucket.get("orders")
    return {"orders": list(orders) if isinstance(orders, list) else []}


def _persist_bucket(operator_settings: dict[str, Any] | None, bucket: dict[str, Any]) -> dict[str, Any]:
    root = dict(operator_settings or {})
    root[BROKER_ORDER_QUEUE_SETTINGS_KEY] = bucket
    return root


def _parse_order(raw: dict[str, Any]) -> BrokerOrderItemOut | None:
    order_id = str(raw.get("id") or "").strip()
    status_raw = str(raw.get("status") or "pending").strip().lower()
    if not order_id or status_raw not in {"pending", "approved", "rejected", "executed", "failed"}:
        return None
    created_raw = raw.get("created_at")
    created_at: datetime
    if isinstance(created_raw, str):
        try:
            created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            created_at = datetime.now(tz=UTC)
    else:
        created_at = datetime.now(tz=UTC)
    reviewed_at: datetime | None = None
    reviewed_raw = raw.get("reviewed_at")
    if isinstance(reviewed_raw, str):
        try:
            reviewed_at = datetime.fromisoformat(reviewed_raw.replace("Z", "+00:00"))
        except ValueError:
            reviewed_at = None
    execution = raw.get("execution") if isinstance(raw.get("execution"), dict) else {}
    return BrokerOrderItemOut(
        id=order_id,
        status=status_raw,  # type: ignore[arg-type]
        venue=str(raw.get("venue") or "polymarket"),
        title=str(raw.get("title") or "Broker order"),
        detail=str(raw.get("detail") or ""),
        notional_usd=float(raw.get("notional_usd") or 0.0),
        payload=dict(raw.get("payload") or {}) if isinstance(raw.get("payload"), dict) else {},
        project_settings=dict(raw.get("project_settings") or {})
        if isinstance(raw.get("project_settings"), dict)
        else {},
        session_id=str(raw.get("session_id")) if raw.get("session_id") else None,
        proposed_by=str(raw.get("proposed_by")) if raw.get("proposed_by") else None,
        created_at=created_at,
        reviewed_at=reviewed_at,
        reviewed_by=str(raw.get("reviewed_by")) if raw.get("reviewed_by") else None,
        review_note=str(raw.get("review_note") or ""),
        execution_status=str(execution.get("status")) if execution.get("status") else None,
        execution_detail=str(execution.get("detail") or execution.get("reason") or "")[:500] or None,
    )


def _list_orders(bucket: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in bucket.get("orders", []) if isinstance(row, dict)]


async def _record_broker_order_audit(
    session: AsyncSession,
    *,
    tenant: Tenant,
    event_type: str,
    message: str,
    order_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    from app.application.services.execution_studio_activity import persist_execution_activity

    await persist_execution_activity(
        session,
        tenant,
        event_type=event_type,
        message=message,
        payload={"order_id": order_id, **(payload or {})},
    )


async def propose_broker_order(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    body: BrokerOrderProposeIn,
) -> BrokerOrderItemOut:
    """Queue a live broker order for operator HITL approval."""

    if not settings.broker_order_queue_enabled:
        msg = "Broker order queue disabled."
        raise ValueError(msg)

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)

    bucket = _queue_bucket(tenant.operator_settings)
    orders = _list_orders(bucket)
    pending = sum(1 for row in orders if str(row.get("status")) == "pending")
    if pending >= MAX_PENDING:
        msg = f"Too many pending broker orders (max {MAX_PENDING})."
        raise ValueError(msg)

    now = datetime.now(tz=UTC)
    order_id = str(uuid.uuid4())
    venue = str(body.venue or "polymarket").strip().lower()
    row: dict[str, Any] = {
        "id": order_id,
        "status": "pending",
        "venue": venue,
        "title": body.title.strip(),
        "detail": body.detail.strip()[:2000],
        "notional_usd": float(body.notional_usd),
        "payload": dict(body.payload),
        "project_settings": dict(body.project_settings),
        "session_id": body.session_id,
        "proposed_by": body.proposed_by or f"operator:{dashboard_user_id}",
        "owner_dashboard_user_id": str(dashboard_user_id),
        "created_at": now.isoformat(),
    }
    orders.insert(0, row)
    bucket["orders"] = orders[:MAX_ORDERS_STORED]
    tenant.operator_settings = _persist_bucket(tenant.operator_settings, bucket)
    await session.flush()

    await _record_broker_order_audit(
        session,
        tenant=tenant,
        event_type="broker_order_proposed",
        message=f"Broker order proposed: {row['title']}",
        order_id=order_id,
        payload={"venue": venue, "notional_usd": row["notional_usd"]},
    )
    _logger.info(
        "broker_order_queue.proposed",
        agent_id="broker_order_queue",
        swarm_id=str(tenant_id),
        task_id=order_id,
        venue=venue,
    )
    parsed = _parse_order(row)
    if parsed is None:
        msg = "Failed to parse proposed order."
        raise ValueError(msg)
    return parsed


async def build_broker_order_queue_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 40,
) -> BrokerOrderQueueSnapshotOut:
    """Load broker order queue for Trading Automation panel."""

    if not settings.broker_order_queue_enabled:
        return BrokerOrderQueueSnapshotOut(
            enabled=False,
            operator_hint="Broker order queue disabled.",
        )

    tenant = await session.get(Tenant, tenant_id)
    bucket = _queue_bucket(tenant.operator_settings if tenant else None)
    cap = max(1, min(limit, MAX_ORDERS_STORED))
    items: list[BrokerOrderItemOut] = []
    pending = executed = rejected = 0
    for raw in _list_orders(bucket):
        parsed = _parse_order(raw)
        if parsed is None:
            continue
        if parsed.status == "pending":
            pending += 1
        elif parsed.status in {"executed", "approved"}:
            executed += 1
        elif parsed.status == "rejected":
            rejected += 1
        items.append(parsed)
        if len(items) >= cap:
            break

    hint = "No pending broker orders."
    if pending:
        hint = f"{pending} broker order(s) awaiting operator approval in HITL queue."

    return BrokerOrderQueueSnapshotOut(
        enabled=True,
        pending_count=pending,
        executed_count=executed,
        rejected_count=rejected,
        items=items,
        operator_hint=hint,
    )


async def review_broker_order(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    order_id: str,
    body: BrokerOrderReviewIn,
    reviewed_by: str | None = None,
) -> BrokerOrderReviewOut:
    """Approve (execute) or reject a pending broker order."""

    if not settings.broker_order_queue_enabled:
        msg = "Broker order queue disabled."
        raise ValueError(msg)

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)

    bucket = _queue_bucket(tenant.operator_settings)
    orders = _list_orders(bucket)
    target: dict[str, Any] | None = None
    for row in orders:
        if str(row.get("id")) == order_id:
            target = row
            break
    if target is None:
        msg = "Broker order not found."
        raise LookupError(msg)
    if str(target.get("status")) != "pending":
        msg = f"Broker order already {target.get('status')}."
        raise ValueError(msg)

    now = datetime.now(tz=UTC)
    reviewer = reviewed_by or f"operator:{dashboard_user_id}"
    target["reviewed_at"] = now.isoformat()
    target["reviewed_by"] = reviewer
    target["review_note"] = body.note.strip()[:500]

    execution_status: str | None = None
    execution_detail: str | None = None
    final_status: BrokerOrderStatus

    if body.decision == "reject":
        target["status"] = "rejected"
        final_status = "rejected"
        await _record_broker_order_audit(
            session,
            tenant=tenant,
            event_type="broker_order_rejected",
            message=f"Broker order rejected: {target.get('title')}",
            order_id=order_id,
            payload={"note": target["review_note"]},
        )
    else:
        execution = await _execute_approved_broker_order(
            session,
            tenant=tenant,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            order=target,
        )
        target["execution"] = execution
        execution_status = str(execution.get("status") or "")
        execution_detail = str(execution.get("detail") or execution.get("reason") or "")[:500] or None
        if execution_status == "executed":
            target["status"] = "executed"
            final_status = "executed"
            await _record_broker_order_audit(
                session,
                tenant=tenant,
                event_type="broker_order_executed",
                message=f"Broker order executed: {target.get('title')}",
                order_id=order_id,
                payload={"venue": target.get("venue"), "status": execution_status},
            )
        else:
            target["status"] = "failed"
            final_status = "failed"
            await _record_broker_order_audit(
                session,
                tenant=tenant,
                event_type="broker_order_failed",
                message=f"Broker order execution failed: {execution_detail or execution_status}",
                order_id=order_id,
                payload={"venue": target.get("venue"), "status": execution_status},
            )

    bucket["orders"] = orders
    tenant.operator_settings = _persist_bucket(tenant.operator_settings, bucket)
    await session.flush()

    _logger.info(
        "broker_order_queue.reviewed",
        agent_id="broker_order_queue",
        swarm_id=str(tenant_id),
        task_id=order_id,
        decision=body.decision,
        final_status=final_status,
    )
    return BrokerOrderReviewOut(
        id=order_id,
        status=final_status,
        execution_status=execution_status,
        execution_detail=execution_detail,
        reviewed_at=now,
    )


async def _execute_approved_broker_order(
    session: AsyncSession,
    *,
    tenant: Tenant,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    order: dict[str, Any],
) -> dict[str, Any]:
    """Run live prediction trade after operator approval."""

    from app.application.services.prediction_market_trading import execute_live_prediction_trade
    from app.application.services.trading_cockpit import ensure_primary_trading_project, sync_project_from_lane
    from app.application.services.trading_cockpit import _trading_lane_bucket

    lane = _trading_lane_bucket(tenant.operator_settings)
    project = await ensure_primary_trading_project(
        session,
        owner_id=dashboard_user_id,
        tenant=tenant,
        lane=lane,
    )
    await sync_project_from_lane(session, project=project, lane=lane)

    project_settings = dict(order.get("project_settings") or {})
    if not project_settings.get("connector_slug") and isinstance(project.settings, dict):
        project_settings.setdefault("connector_slug", project.settings.get("connector_slug"))
    project_settings.setdefault("venue", order.get("venue") or "polymarket")
    project_settings.setdefault("trading_mode", "real")

    payload = dict(order.get("payload") or {})
    payload["operator_confirmed"] = True
    payload["human_approval_confirmed"] = True
    payload["human_approval_ticket"] = f"hitl:{order.get('id')}"

    return await execute_live_prediction_trade(
        session,
        project=project,
        payload=payload,
        project_settings=project_settings,
    )


async def compose_broker_order_inbox_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Map pending broker orders to unified approval inbox rows."""

    snapshot = await build_broker_order_queue_snapshot(session, tenant_id=tenant_id, limit=limit)
    rows: list[dict[str, Any]] = []
    for item in snapshot.items:
        if item.status != "pending":
            continue
        rows.append(
            {
                "id": item.id,
                "title": item.title,
                "detail": item.detail or f"{item.venue} · ${item.notional_usd:.2f} notional",
                "created_at": item.created_at,
                "venue": item.venue,
                "notional_usd": item.notional_usd,
            },
        )
    return rows


async def queue_live_trade_from_agent(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    payload: dict[str, Any],
    project_settings: dict[str, Any],
    session_id: str | None = None,
    proposed_by: str | None = None,
) -> dict[str, Any]:
    """When live trade needs HITL, enqueue instead of executing immediately."""

    venue = str(project_settings.get("venue") or payload.get("venue") or "polymarket").strip().lower()
    symbol = str(
        payload.get("market_ticker") or payload.get("symbol") or payload.get("market_id") or "order",
    ).strip()
    notional = float(payload.get("notional_usd") or 0.0)
    if notional <= 0:
        try:
            count = int(float(payload.get("count") or payload.get("quantity") or 0))
            cents = int(float(payload.get("yes_price") or payload.get("price_cents") or 0))
            notional = (count * cents) / 100.0
        except (TypeError, ValueError):
            notional = 0.0

    title = str(payload.get("title") or f"{venue} · {symbol}").strip()[:200]
    detail = str(payload.get("detail") or payload.get("rationale") or "Agent proposed live broker order.").strip()

    item = await propose_broker_order(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        body=BrokerOrderProposeIn(
            venue=venue,
            title=title,
            detail=detail[:2000],
            notional_usd=notional,
            payload=payload,
            project_settings=project_settings,
            session_id=session_id,
            proposed_by=proposed_by,
        ),
    )
    return {
        "status": "queued",
        "reason": "broker_hitl_required",
        "detail": "Order queued for operator approval (RA5 HITL).",
        "order_id": item.id,
        "workspace_href": item.workspace_href,
        "verified": False,
    }


__all__ = [
    "BROKER_ORDER_QUEUE_SETTINGS_KEY",
    "BrokerOrderItemOut",
    "BrokerOrderProposeIn",
    "BrokerOrderQueueSnapshotOut",
    "BrokerOrderReviewIn",
    "BrokerOrderReviewOut",
    "build_broker_order_queue_snapshot",
    "compose_broker_order_inbox_items",
    "propose_broker_order",
    "queue_live_trade_from_agent",
    "review_broker_order",
]
