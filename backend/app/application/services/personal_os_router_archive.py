"""POS-G4 — Archive commercial API routers when Personal OS mode is active."""

from __future__ import annotations

from typing import Final

from fastapi import HTTPException, status

# Commercial/revenue/trading surfaces not used in Personal OS daily stack.
PERSONAL_OS_ARCHIVED_API_TAGS: Final[frozenset[str]] = frozenset(
    {
        "commerce",
        "commerce_webhooks",
        "billing",
        "tools_marketplace",
        "micro_saas_factory",
        "harness_products",
        "content_pack_factory",
        "factory_readiness",
        "trading_cockpit",
        "trading_content_hybrid",
        "prediction_markets",
        "virtual_company",
        "media_agency",
        "journal_studio",
        "jobs",
        "simulations",
        "skill_marketplace_ugc",
    },
)


def personal_os_commercial_api_enabled() -> bool:
    """Return False when Personal OS archives commercial HTTP surface (POS-G4)."""

    from app.core.config import settings

    return not settings.personal_os_mode_enabled


def require_commercial_api() -> None:
    """Raise 404 when commercial API is archived for Personal OS."""

    if personal_os_commercial_api_enabled():
        return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="commercial_api_archived_in_personal_os",
    )


__all__ = [
    "PERSONAL_OS_ARCHIVED_API_TAGS",
    "personal_os_commercial_api_enabled",
    "require_commercial_api",
]
