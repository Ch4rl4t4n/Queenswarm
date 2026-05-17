"""Registry behaviour for MCP / outbound connector stubs."""

from __future__ import annotations

import pytest

from app.infrastructure.connectors.base import BaseConnector, ConnectorAuthEnvelope
from app.infrastructure.connectors.registry import ConnectorRegistry


class AlphaConnector(BaseConnector):
    slug = "alpha"

    async def ping(self, auth: ConnectorAuthEnvelope) -> bool:
        return bool(auth.bearer_header())


def test_connector_registry_duplicate_slug_raises() -> None:
    """Second registration sharing slug must explode."""

    reg = ConnectorRegistry()
    reg.register(AlphaConnector)
    with pytest.raises(ValueError):
        reg.register(AlphaConnector)


def test_resolve_builtin_mcp_placeholder() -> None:
    """Starter adapter registers with slug ``mcp_placeholder``."""

    from app.infrastructure.connectors.registry import registry as global_registry

    cls = global_registry.resolve("mcp_placeholder")
    assert getattr(cls, "slug", "").lower() == "mcp_placeholder"
