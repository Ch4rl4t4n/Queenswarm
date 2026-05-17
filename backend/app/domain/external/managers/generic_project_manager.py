"""Generic integration lane — safe echo/simulate surface for bespoke workloads."""

from __future__ import annotations

from typing import Any


class GenericProjectManager:
    """Passes verified simulations only when callers explicitly request ``simulate`` mode."""

    async def handle(self, *, action: str, payload: dict[str, Any], project_settings: dict[str, Any]) -> dict[str, Any]:
        """Echo structured payloads or emit deterministic simulations."""

        if action == "echo":
            return {"status": "ok", "echo": payload, "verified": True}

        if action == "simulate":
            marker = str(project_settings.get("verification_marker") or "generic-pass")
            return {"status": "simulated", "marker": marker, "payload": payload, "verified": True}

        msg = f"Unsupported generic action {action!r}."
        raise ValueError(msg)


__all__ = ["GenericProjectManager"]
