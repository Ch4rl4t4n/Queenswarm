"""Food ordering façade — validates structured carts before downstream POS/webhooks."""

from __future__ import annotations

from typing import Any


class FoodOrderingManager:
    """Deterministic validation stub suitable for connecting external POS adapters."""

    async def handle(self, *, action: str, payload: dict[str, Any], project_settings: dict[str, Any]) -> dict[str, Any]:
        """Validate lightweight ordering payloads.

        Args:
            action: ``preview_cart`` or ``submit_order``.
            payload: Remote caller JSON.
            project_settings: Integration knobs such as ``service_radius_km``.

        Raises:
            ValueError: When required meal-plan keys are absent.
        """

        _ = project_settings
        vendor = str(payload.get("vendor_id") or "").strip()
        if not vendor:
            msg = "payload.vendor_id is required."
            raise ValueError(msg)

        items = payload.get("items")
        if not isinstance(items, list) or not items:
            msg = "payload.items must be a non-empty list."
            raise ValueError(msg)

        normalized: list[dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict):
                msg = "Each cart item must be an object."
                raise ValueError(msg)
            sku = str(raw.get("sku") or "").strip()
            if not sku:
                msg = "Each cart item requires sku."
                raise ValueError(msg)
            try:
                qty = int(raw.get("qty") or 0)
            except (TypeError, ValueError) as exc:
                msg = "Cart qty must be integral."
                raise ValueError(msg) from exc
            if qty < 1:
                msg = "Cart qty must be >= 1."
                raise ValueError(msg)
            normalized.append({"sku": sku, "qty": qty})

        if action == "preview_cart":
            return {"status": "ok", "vendor_id": vendor, "items": normalized, "verified": True}

        if action == "submit_order":
            customer_ref = str(payload.get("customer_ref") or "").strip()
            if not customer_ref:
                msg = "submit_order requires payload.customer_ref."
                raise ValueError(msg)
            return {
                "status": "submitted",
                "vendor_id": vendor,
                "items": normalized,
                "customer_ref": customer_ref[:160],
                "verified": False,
            }

        msg = f"Unsupported food action {action!r}."
        raise ValueError(msg)


__all__ = ["FoodOrderingManager"]
