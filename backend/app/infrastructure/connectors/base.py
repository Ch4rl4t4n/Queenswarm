"""Abstract connector contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel


class ConnectorAuthEnvelope(BaseModel):
    """Portable secret bundle for outbound connector calls."""

    model_config = {"extra": "forbid"}

    kind: str
    oauth2_access_token: str | None = None
    oauth2_refresh_token: str | None = None
    oauth2_token_endpoint: str | None = None
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    api_key: str | None = None
    scopes: tuple[str, ...] = ()

    def bearer_header(self) -> dict[str, str]:
        """Return Authorization header fragments when bearer token exists."""

        if isinstance(self.oauth2_access_token, str) and self.oauth2_access_token.strip():
            return {"Authorization": f"Bearer {self.oauth2_access_token.strip()}"}
        if isinstance(self.api_key, str) and self.api_key.strip():
            return {"Authorization": f"Bearer {self.api_key.strip()}"}
        return {}


class BaseConnector(ABC):
    """One connector = one external surface (OAuth2 or API-key driven)."""

    slug: ClassVar[str]

    @abstractmethod
    async def ping(self, auth: ConnectorAuthEnvelope) -> bool:
        """Return ``True`` when credentials present and remote handshake plausible."""

        raise NotImplementedError

    async def introspect_capabilities(self, auth: ConnectorAuthEnvelope) -> dict[str, Any]:
        """Optional capability listing for dashboards."""

        healthy = await self.ping(auth)
        return {"ok": healthy, "slug": self.slug}
