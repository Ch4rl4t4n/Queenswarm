"""Centralized agentic gates — operator approval, real money, social publish.

Maps markdown skills (operator-approval-gate, real-money-risk-gate, social-simulate-first)
to enforceable runtime checks used by Execution Studio, trading, and publish lanes.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.execution_studio import RiskTier
from app.core.config import settings

ExecutionMode = Literal["draft", "simulate", "live"]


class GateKind(StrEnum):
    """Known gate types for audit logs and UI chips."""

    OPERATOR_APPROVAL = "operator_approval"
    REAL_MONEY = "real_money"
    SOCIAL_PUBLISH = "social_publish"


class GateDecision(BaseModel):
    """Result of a gate evaluation."""

    model_config = ConfigDict(extra="ignore")

    allowed: bool
    gate: GateKind
    error_code: str | None = None
    message: str | None = None
    risk_tier: RiskTier | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def evaluate_live_execution_gate(
    *,
    mode: ExecutionMode,
    risk_tier: RiskTier,
    operator_confirmed: bool,
    live_requires_approval: bool = True,
    connector_slug: str = "",
) -> GateDecision:
    """Gate live connector invokes (write / publish / financial).

    Used by Execution Studio before upstream HTTP calls.
    """

    if mode != "live":
        return GateDecision(allowed=True, gate=GateKind.OPERATOR_APPROVAL, risk_tier=risk_tier)

    slug = connector_slug.strip().lower()
    if risk_tier == "financial" or any(token in slug for token in ("stripe", "shopify", "billing")):
        financial = evaluate_real_money_gate(
            operator_confirmed=operator_confirmed,
            action=f"connector:{slug or 'unknown'}",
            paper_mode=False,
        )
        if not financial.allowed:
            return financial

    if live_requires_approval and risk_tier in {"write", "publish", "financial"} and not operator_confirmed:
        return GateDecision(
            allowed=False,
            gate=GateKind.OPERATOR_APPROVAL,
            error_code="approval_required",
            message="Live write/publish/financial actions require operator approval.",
            risk_tier=risk_tier,
            metadata={"connector_slug": slug},
        )

    return GateDecision(allowed=True, gate=GateKind.OPERATOR_APPROVAL, risk_tier=risk_tier)


def evaluate_real_money_gate(
    *,
    operator_confirmed: bool,
    action: str,
    paper_mode: bool = True,
    daily_loss_ok: bool = True,
    position_size_ok: bool = True,
) -> GateDecision:
    """Gate live financial actions (trading, Stripe capture, order mutations).

    Paper mode always passes — live requires explicit operator confirm + risk caps.
    """

    if paper_mode:
        return GateDecision(
            allowed=True,
            gate=GateKind.REAL_MONEY,
            metadata={"action": action, "paper_mode": True},
        )

    if not operator_confirmed:
        return GateDecision(
            allowed=False,
            gate=GateKind.REAL_MONEY,
            error_code="real_money_approval_required",
            message="Real-money action blocked — operator approval required.",
            metadata={"action": action},
        )

    if not daily_loss_ok:
        return GateDecision(
            allowed=False,
            gate=GateKind.REAL_MONEY,
            error_code="daily_loss_cap",
            message="Daily loss cap reached — trading/payments halted.",
            metadata={"action": action},
        )

    if not position_size_ok:
        return GateDecision(
            allowed=False,
            gate=GateKind.REAL_MONEY,
            error_code="position_size_cap",
            message="Order exceeds max position size.",
            metadata={"action": action},
        )

    return GateDecision(allowed=True, gate=GateKind.REAL_MONEY, metadata={"action": action})


def evaluate_social_publish_gate(
    *,
    mode: ExecutionMode,
    operator_confirmed: bool,
    effective_confirmed: bool,
    confirm_reason: str = "",
    live_enabled: bool | None = None,
) -> GateDecision:
    """Gate live social publish (simulate-first default).

    Wraps SOCIAL_PUBLISH_LIVE_ENABLED + operator confirm + trusted-auto reasons.
    """

    live_flag = settings.social_publish_live_enabled if live_enabled is None else live_enabled

    if mode != "live":
        return GateDecision(allowed=True, gate=GateKind.SOCIAL_PUBLISH, metadata={"mode": mode})

    if not live_flag:
        return GateDecision(
            allowed=False,
            gate=GateKind.SOCIAL_PUBLISH,
            error_code="live_disabled",
            message="Live social publish disabled — set SOCIAL_PUBLISH_LIVE_ENABLED=true after OAuth.",
        )

    if not effective_confirmed:
        reason_messages = {
            "trusted_auto_global_off": "Live publish requires operator_confirmed=true (trusted auto disabled globally).",
            "live_disabled": "Live social publish disabled.",
            "tenant_missing": "Tenant context required for live publish.",
            "trusted_auto_tenant_off": "Enable trusted auto-publish in Social publish settings or confirm manually.",
            "channel_manual_mode": "Channel is manual mode — click Live with confirmation.",
            "pack_not_simulated": "Run Simulate on this pack before live (or auto-live).",
            "insufficient_channel_simulates": (
                "Channel needs more successful simulates before auto-live — keep using manual Live or lower threshold."
            ),
        }
        return GateDecision(
            allowed=False,
            gate=GateKind.SOCIAL_PUBLISH,
            error_code=confirm_reason or "approval_required",
            message=reason_messages.get(
                confirm_reason,
                "Live publish requires operator_confirmed=true.",
            ),
            metadata={"operator_confirmed": operator_confirmed, "confirm_reason": confirm_reason},
        )

    return GateDecision(allowed=True, gate=GateKind.SOCIAL_PUBLISH, metadata={"mode": "live"})


__all__ = [
    "GateDecision",
    "GateKind",
    "evaluate_live_execution_gate",
    "evaluate_real_money_gate",
    "evaluate_social_publish_gate",
]
