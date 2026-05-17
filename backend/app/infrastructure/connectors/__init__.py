"""Phase 0 connector preparation — MCP-style adapters backed by Postgres vault AES."""

from app.infrastructure.connectors.base import BaseConnector, ConnectorAuthEnvelope
from app.infrastructure.connectors.registry import ConnectorRegistry, registry

__all__ = ["BaseConnector", "ConnectorAuthEnvelope", "ConnectorRegistry", "registry"]
