"""In-process connector class registry."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeVar

from app.infrastructure.connectors.base import BaseConnector

C = TypeVar("C", bound=type[BaseConnector])


class ConnectorRegistry:
    """Maps connector slugs to concrete :class:`~app.connectors.base.BaseConnector`."""

    def __init__(self) -> None:
        """Initialize registry metadata."""

        self._connectors: dict[str, type[BaseConnector]] = {}

    def register(self, cls: C) -> C:
        """Register ``cls.slug`` uniquely."""

        key = getattr(cls, "slug", "").strip().lower()
        if not key:
            msg = "Connector class requires non-empty slug"
            raise ValueError(msg)
        if key in self._connectors:
            msg = f"duplicate connector slug: {key}"
            raise ValueError(msg)
        self._connectors[key] = cls
        return cls

    def unregister(self, slug: str) -> None:
        """Remove slug (mostly tests)."""

        self._connectors.pop(slug.strip().lower(), None)

    def resolve(self, slug: str) -> type[BaseConnector]:
        """Return connector class."""

        lowered = slug.strip().lower()
        if lowered not in self._connectors:
            msg = f"connector not registered: {slug}"
            raise KeyError(msg)
        return self._connectors[lowered]

    def slugs(self) -> tuple[str, ...]:
        """Return registered slugs (stable order)."""

        return tuple(sorted(self._connectors))

    async def merged_slugs(self, session: Any) -> tuple[str, ...]:
        """Return static registry slugs plus active dynamic Postgres MCP slugs."""

        from app.infrastructure.connectors.dynamic.hub import load_active_snapshots

        snaps = await load_active_snapshots(session)
        dynamic = tuple(s.slug for s in snaps if s.is_active)
        return tuple(sorted(set(self.slugs()).union(dynamic)))

    def all_classes(self) -> Iterable[type[BaseConnector]]:
        """Iterate registered connectors."""

        return self._connectors.values()


registry = ConnectorRegistry()

from app.infrastructure.connectors.mcp_adapter import MCPAdapter as _BuiltinMCPAdapter  # noqa: E402 circular-safe import

registry.register(_BuiltinMCPAdapter)

__all__ = ["ConnectorRegistry", "registry"]
