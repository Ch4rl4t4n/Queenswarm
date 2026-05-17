"""Hosted OAuth consent (Phase 4.0) — PKCE + Redis-bound state + vault + Dynamic Hub."""

from __future__ import annotations

from app.application.services.oauth_consent.providers import (
    OAUTH_SURFACES,
    OAuthSurfaceSpec,
    oauth_catalog_snapshot,
)
from app.application.services.oauth_consent.service import (
    complete_oauth_callback,
    start_oauth_authorization,
)

__all__ = [
    "OAUTH_SURFACES",
    "OAuthSurfaceSpec",
    "complete_oauth_callback",
    "oauth_catalog_snapshot",
    "start_oauth_authorization",
]
