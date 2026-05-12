#!/usr/bin/env python3
"""Bootstrap the default dashboard operator account (idempotent, safe to re-run on boot)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pyotp
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.core.database import async_session
from app.models.dashboard_user import DashboardUser
from app.services.dashboard_crypto import hash_dashboard_password

_ADMIN_EMAIL = "admin@queenswarm.love"


async def ensure_dashboard_admin() -> dict[str, str]:
    """Insert the primary operator when missing.

    Returns:
        Status metadata for Compose logs (never includes password).
    """

    initial_password = os.environ.get("DASHBOARD_ADMIN_INITIAL_PASSWORD", "change-me-password")
    env_secret = os.environ.get("DASHBOARD_ADMIN_TOTP_SECRET")

    async with async_session() as session:
        exists = await session.scalar(select(DashboardUser).where(DashboardUser.email == _ADMIN_EMAIL))
        if exists is not None:
            return {"status": "exists", "email": _ADMIN_EMAIL}

        secret = str(env_secret).strip() if env_secret else ""
        if not secret:
            secret = pyotp.random_base32()
        row = DashboardUser(
            email=_ADMIN_EMAIL,
            password_hash=hash_dashboard_password(initial_password),
            display_name="Hive Administrator",
            totp_secret=secret,
            totp_verified_at=None,
            totp_required=True,
            is_admin=True,
            is_active=True,
        )
        session.add(row)
        await session.commit()

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=_ADMIN_EMAIL, issuer_name=settings.dashboard_totpissuer)
    return {
        "status": "created",
        "email": _ADMIN_EMAIL,
        "otpauth_uri": uri,
    }


def main() -> None:
    stats = asyncio.run(ensure_dashboard_admin())
    print(f"dashboard_operator_seed {stats!s}")
    if stats.get("status") == "created" and stats.get("otpauth_uri"):
        print("dashboard_operator_seed_action=scan_otpauth_uri with Google Authenticator / 1Password")
    if stats.get("status") == "exists":
        print("dashboard_operator_seed_note=admin already present (no OTP URI printed)")


if __name__ == "__main__":
    main()
