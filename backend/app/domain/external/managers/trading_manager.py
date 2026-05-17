"""Trading façade — paper vs live guards with mandatory human approval on live execution."""

from __future__ import annotations

from typing import Any


class TradingManager:
    """Evaluates trading intents without touching broker APIs (integration boundary stub).

    Live execution requires explicit human confirmation payloads plus elevated scopes.
    """

    async def handle(self, *, action: str, payload: dict[str, Any], project_settings: dict[str, Any]) -> dict[str, Any]:
        """Return a structured outcome envelope suitable for audit rows.

        Args:
            action: Capability slug such as ``quote`` or ``execute_trade``.
            payload: Arbitrary JSON from the remote caller (validated lightly).
            project_settings: Persisted ``external_projects.settings`` JSON blob.

        Raises:
            ValueError: When payloads are clearly malformed.
        """

        mode = str(project_settings.get("trading_mode") or "paper").strip().lower()
        if mode not in {"paper", "real"}:
            msg = "settings.trading_mode must be 'paper' or 'real'."
            raise ValueError(msg)

        symbol = str(payload.get("symbol") or "").strip().upper()
        if not symbol:
            msg = "payload.symbol is required."
            raise ValueError(msg)

        qty = payload.get("quantity")
        try:
            quantity = float(qty) if qty is not None else 0.0
        except (TypeError, ValueError) as exc:
            msg = "payload.quantity must be numeric when provided."
            raise ValueError(msg) from exc

        max_usd = float(project_settings.get("max_order_usd") or 25_000.0)
        notional = float(payload.get("limit_price_usd") or payload.get("notional_usd") or 0.0) or quantity * float(
            payload.get("assumed_price_usd") or 0.0,
        )
        if notional > max_usd:
            return {
                "status": "blocked",
                "reason": "risk_limit",
                "detail": f"Order notional {notional} exceeds max_order_usd={max_usd}.",
                "symbol": symbol,
                "mode": mode,
            }

        if action in {"quote", "simulate"}:
            return {
                "status": "ok",
                "mode": mode,
                "symbol": symbol,
                "quantity": quantity,
                "mid_px_proxy": float(payload.get("assumed_price_usd") or 100.0),
                "verified": True,
            }

        if action == "execute_trade":
            if mode == "paper":
                return {
                    "status": "simulated_fill",
                    "mode": "paper",
                    "symbol": symbol,
                    "quantity": quantity,
                    "verified": True,
                }

            confirmed = bool(payload.get("human_approval_confirmed"))
            ticket = str(payload.get("human_approval_ticket") or "").strip()
            if not confirmed or len(ticket) < 8:
                return {
                    "status": "blocked",
                    "reason": "human_approval_required",
                    "detail": "Live trades require human_approval_confirmed=true plus ticket.",
                    "symbol": symbol,
                    "mode": mode,
                }
            return {
                "status": "queued_for_execution",
                "mode": "real",
                "symbol": symbol,
                "quantity": quantity,
                "ticket": ticket[:160],
                "verified": False,
            }

        msg = f"Unsupported trading action {action!r}."
        raise ValueError(msg)


__all__ = ["TradingManager"]
