"""Track P RA3 — Unified broker guardrails (Polymarket + Robinhood)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

BROKER_GUARDRAILS_SETTINGS_KEY = "broker_guardrails"

ApproveMode = Literal["always", "simulate_first", "trusted_auto"]
PolicySource = Literal["deployment", "tenant"]
BrokerVenue = Literal["polymarket", "robinhood"]

SUPPORTED_VENUES: frozenset[str] = frozenset({"polymarket", "robinhood"})

MAX_ORDER_MIN = 1.0
MAX_ORDER_MAX = 100_000.0
DAILY_CAP_MIN = 10.0
DAILY_CAP_MAX = 500_000.0


class BrokerGuardrailsOut(BaseModel):
    """Tenant broker guardrails snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    kill_switch: bool = False
    max_order_usd: float = 100.0
    daily_cap_usd: float = 500.0
    approve_mode: ApproveMode = "always"
    venues: list[str] = Field(default_factory=lambda: ["polymarket", "robinhood"])
    daily_spent_usd: float = 0.0
    daily_spend_date: str | None = None
    source: PolicySource = "deployment"
    updated_at: datetime | None = None
    workspace_href: str = "/apps-tools/trading-automation?section=guardrails#broker-guardrails"

    @field_validator("max_order_usd")
    @classmethod
    def _clamp_max_order(cls, value: float) -> float:
        return max(MAX_ORDER_MIN, min(float(value), MAX_ORDER_MAX))

    @field_validator("daily_cap_usd")
    @classmethod
    def _clamp_daily_cap(cls, value: float) -> float:
        return max(DAILY_CAP_MIN, min(float(value), DAILY_CAP_MAX))


class BrokerGuardrailsPatchIn(BaseModel):
    """Operator PATCH body for broker guardrails."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    kill_switch: bool | None = None
    max_order_usd: float | None = Field(default=None, ge=MAX_ORDER_MIN, le=MAX_ORDER_MAX)
    daily_cap_usd: float | None = Field(default=None, ge=DAILY_CAP_MIN, le=DAILY_CAP_MAX)
    approve_mode: ApproveMode | None = None
    venues: list[str] | None = None

    @field_validator("venues")
    @classmethod
    def _sanitize_venues(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        seen: set[str] = set()
        out: list[str] = []
        for raw in value:
            venue = str(raw).strip().lower()
            if venue not in SUPPORTED_VENUES or venue in seen:
                continue
            seen.add(venue)
            out.append(venue)
        if not out:
            msg = "At least one venue (polymarket or robinhood) is required."
            raise ValueError(msg)
        return out


class BrokerOrderGateResult(BaseModel):
    """Outcome of broker guardrails pre-trade gate."""

    model_config = ConfigDict(extra="ignore")

    allowed: bool
    reason: str | None = None
    detail: str | None = None
    effective_max_order_usd: float | None = None
    daily_spent_usd: float = 0.0
    daily_cap_usd: float | None = None
    kill_switch: bool = False
    approve_mode: ApproveMode = "always"


def _utc_today() -> str:
    return datetime.now(tz=UTC).date().isoformat()


def _deployment_defaults() -> BrokerGuardrailsOut:
    mode_raw = settings.broker_guardrails_default_approve_mode
    approve_mode: ApproveMode = "always"
    if mode_raw in {"always", "simulate_first", "trusted_auto"}:
        approve_mode = mode_raw  # type: ignore[assignment]
    return BrokerGuardrailsOut(
        enabled=settings.broker_guardrails_enabled,
        kill_switch=False,
        max_order_usd=float(settings.broker_guardrails_default_max_order_usd),
        daily_cap_usd=float(settings.broker_guardrails_default_daily_cap_usd),
        approve_mode=approve_mode,
        venues=["polymarket", "robinhood"],
        source="deployment",
    )


def _guardrails_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(BROKER_GUARDRAILS_SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def _read_daily_spend(bucket: dict[str, Any]) -> tuple[float, str | None]:
    spend_raw = bucket.get("daily_spend")
    if not isinstance(spend_raw, dict):
        return 0.0, None
    date_raw = spend_raw.get("date")
    if not isinstance(date_raw, str) or date_raw != _utc_today():
        return 0.0, date_raw if isinstance(date_raw, str) else None
    try:
        spent = float(spend_raw.get("spent_usd") or 0.0)
    except (TypeError, ValueError):
        spent = 0.0
    return max(0.0, spent), date_raw


def _guardrails_from_bucket(bucket: dict[str, Any]) -> BrokerGuardrailsOut:
    base = _deployment_defaults()
    if not bucket:
        return base
    mode_raw = str(bucket.get("approve_mode", base.approve_mode))
    approve_mode: ApproveMode = base.approve_mode
    if mode_raw in {"always", "simulate_first", "trusted_auto"}:
        approve_mode = mode_raw  # type: ignore[assignment]
    venues_raw = bucket.get("venues")
    venues = list(base.venues)
    if isinstance(venues_raw, list):
        try:
            venues = BrokerGuardrailsPatchIn.model_validate({"venues": venues_raw}).venues or venues
        except ValueError:
            venues = list(base.venues)
    spent, spend_date = _read_daily_spend(bucket)
    merged = base.model_copy(
        update={
            "enabled": bool(bucket.get("enabled", base.enabled)),
            "kill_switch": bool(bucket.get("kill_switch", base.kill_switch)),
            "max_order_usd": float(bucket.get("max_order_usd", base.max_order_usd)),
            "daily_cap_usd": float(bucket.get("daily_cap_usd", base.daily_cap_usd)),
            "approve_mode": approve_mode,
            "venues": venues,
            "daily_spent_usd": spent,
            "daily_spend_date": spend_date if spend_date == _utc_today() else _utc_today() if spent else spend_date,
            "source": "tenant",
            "updated_at": bucket.get("updated_at"),
        },
    )
    return BrokerGuardrailsOut.model_validate(merged.model_dump(mode="python"))


async def get_broker_guardrails(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> BrokerGuardrailsOut:
    """Load tenant broker guardrails."""

    tenant = await session.get(Tenant, tenant_id)
    bucket = _guardrails_bucket(tenant.operator_settings if tenant else None)
    return _guardrails_from_bucket(bucket)


def approve_mode_to_execution_flow(mode: ApproveMode) -> str:
    """Map broker approve mode to trading lane execution_flow."""

    if mode == "simulate_first":
        return "simulate_first"
    if mode == "trusted_auto":
        return "trusted_auto"
    return "manual_approve"


def execution_flow_to_approve_mode(flow: str | None) -> ApproveMode:
    """Map trading lane execution_flow to broker approve mode."""

    raw = str(flow or "").strip().lower()
    if raw == "simulate_first":
        return "simulate_first"
    if raw == "trusted_auto":
        return "trusted_auto"
    return "always"


def merge_broker_guardrails_patch(
    operator_settings: dict[str, Any] | None,
    saved: BrokerGuardrailsOut,
) -> dict[str, Any]:
    """Persist broker guardrails bucket and sync trading lane risk caps."""

    from app.application.services.trading_cockpit import merge_trading_lane_patch

    root = dict(operator_settings or {})
    bucket = _guardrails_bucket(root)
    spent, spend_date = _read_daily_spend(bucket)
    root[BROKER_GUARDRAILS_SETTINGS_KEY] = {
        "enabled": saved.enabled,
        "kill_switch": saved.kill_switch,
        "max_order_usd": saved.max_order_usd,
        "daily_cap_usd": saved.daily_cap_usd,
        "approve_mode": saved.approve_mode,
        "venues": saved.venues,
        "daily_spend": bucket.get("daily_spend")
        if isinstance(bucket.get("daily_spend"), dict) and spend_date == _utc_today()
        else {"date": _utc_today(), "spent_usd": spent if spend_date == _utc_today() else 0.0},
        "updated_at": saved.updated_at.isoformat() if saved.updated_at else datetime.now(tz=UTC).isoformat(),
    }
    root = merge_trading_lane_patch(
        root,
        {
            "execution_flow": approve_mode_to_execution_flow(saved.approve_mode),
            "risk": {
                "max_order_usd": saved.max_order_usd,
                "max_daily_loss_usd": saved.daily_cap_usd,
            },
        },
    )
    return root


async def save_broker_guardrails(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    patch: BrokerGuardrailsPatchIn,
) -> BrokerGuardrailsOut:
    """Persist tenant broker guardrails and sync trading lane."""

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)

    current = await get_broker_guardrails(session, tenant_id=tenant_id)
    data = current.model_dump(mode="python")
    for key, value in patch.model_dump(exclude_unset=True).items():
        if value is not None:
            data[key] = value
    data["source"] = "tenant"
    data["updated_at"] = datetime.now(tz=UTC)
    saved = BrokerGuardrailsOut.model_validate(data)

    tenant.operator_settings = merge_broker_guardrails_patch(tenant.operator_settings, saved)
    await session.flush()
    _logger.info(
        "broker_guardrails.saved",
        agent_id="broker_guardrails",
        swarm_id=str(tenant_id),
        kill_switch=saved.kill_switch,
        max_order_usd=saved.max_order_usd,
        approve_mode=saved.approve_mode,
    )
    return saved


def evaluate_broker_order_gate(
    guardrails: BrokerGuardrailsOut,
    *,
    venue: str,
    notional_usd: float,
    operator_confirmed: bool = False,
) -> BrokerOrderGateResult:
    """Deterministic pre-trade gate shared by Polymarket and Robinhood lanes."""

    venue_norm = str(venue or "").strip().lower()
    if not guardrails.enabled:
        return BrokerOrderGateResult(allowed=True, approve_mode=guardrails.approve_mode)

    if guardrails.kill_switch:
        return BrokerOrderGateResult(
            allowed=False,
            reason="kill_switch",
            detail="Broker kill switch is ON — all live orders blocked.",
            kill_switch=True,
            approve_mode=guardrails.approve_mode,
        )

    if venue_norm and venue_norm not in {v.lower() for v in guardrails.venues}:
        return BrokerOrderGateResult(
            allowed=False,
            reason="venue_disabled",
            detail=f"Venue {venue_norm!r} not enabled in broker guardrails.",
            approve_mode=guardrails.approve_mode,
        )

    effective_max = float(guardrails.max_order_usd)
    if notional_usd > effective_max > 0:
        return BrokerOrderGateResult(
            allowed=False,
            reason="max_order",
            detail=f"Notional ${notional_usd:.2f} exceeds broker max_order_usd ${effective_max:.2f}.",
            effective_max_order_usd=effective_max,
            approve_mode=guardrails.approve_mode,
        )

    projected = float(guardrails.daily_spent_usd) + max(0.0, notional_usd)
    if projected > float(guardrails.daily_cap_usd) > 0:
        return BrokerOrderGateResult(
            allowed=False,
            reason="daily_cap",
            detail=(
                f"Daily cap ${guardrails.daily_cap_usd:.2f} would be exceeded "
                f"(spent ${guardrails.daily_spent_usd:.2f} + order ${notional_usd:.2f})."
            ),
            daily_spent_usd=guardrails.daily_spent_usd,
            daily_cap_usd=guardrails.daily_cap_usd,
            approve_mode=guardrails.approve_mode,
        )

    if guardrails.approve_mode == "always" and not operator_confirmed:
        return BrokerOrderGateResult(
            allowed=False,
            reason="approval_required",
            detail="approve_mode=always — operator_confirmed required before live execution.",
            effective_max_order_usd=effective_max,
            daily_spent_usd=guardrails.daily_spent_usd,
            daily_cap_usd=guardrails.daily_cap_usd,
            approve_mode=guardrails.approve_mode,
        )

    return BrokerOrderGateResult(
        allowed=True,
        effective_max_order_usd=effective_max,
        daily_spent_usd=guardrails.daily_spent_usd,
        daily_cap_usd=guardrails.daily_cap_usd,
        approve_mode=guardrails.approve_mode,
    )


async def record_broker_daily_spend(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    notional_usd: float,
) -> None:
    """Increment tenant daily spend counter after verified live fill."""

    if notional_usd <= 0:
        return
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return
    root = dict(tenant.operator_settings or {})
    bucket = _guardrails_bucket(root)
    today = _utc_today()
    spent, _ = _read_daily_spend(bucket)
    saved_fields = {
        key: bucket[key]
        for key in ("enabled", "kill_switch", "max_order_usd", "daily_cap_usd", "approve_mode", "venues", "updated_at")
        if key in bucket
    }
    if not saved_fields:
        defaults = _deployment_defaults()
        saved_fields = {
            "enabled": defaults.enabled,
            "kill_switch": defaults.kill_switch,
            "max_order_usd": defaults.max_order_usd,
            "daily_cap_usd": defaults.daily_cap_usd,
            "approve_mode": defaults.approve_mode,
            "venues": defaults.venues,
        }
    root[BROKER_GUARDRAILS_SETTINGS_KEY] = {
        **saved_fields,
        "daily_spend": {"date": today, "spent_usd": round(spent + float(notional_usd), 4)},
    }
    tenant.operator_settings = root
    await session.flush()


__all__ = [
    "BROKER_GUARDRAILS_SETTINGS_KEY",
    "BrokerGuardrailsOut",
    "BrokerGuardrailsPatchIn",
    "BrokerOrderGateResult",
    "approve_mode_to_execution_flow",
    "evaluate_broker_order_gate",
    "execution_flow_to_approve_mode",
    "get_broker_guardrails",
    "merge_broker_guardrails_patch",
    "record_broker_daily_spend",
    "save_broker_guardrails",
]
