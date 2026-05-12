#!/usr/bin/env python3
"""Create or update a dashboard operator with password auth (no mandatory TOTP).

Secrets must come from env ``QS_BOOTSTRAP_PASSWORD`` — never hard-code production passwords.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.database import async_session
from app.models.dashboard_user import DashboardUser
from app.services.dashboard_crypto import hash_dashboard_password


async def upsert_operator(*, email: str, password: str, display_name: str | None, is_admin: bool) -> str:
    """Insert or update ``DashboardUser``; disable ``totp_required``."""

    email_clean = email.strip().lower()
    hashed = hash_dashboard_password(password)

    async with async_session() as session:
        existing = await session.scalar(select(DashboardUser).where(DashboardUser.email == email_clean))
        if existing is None:
            session.add(
                DashboardUser(
                    email=email_clean,
                    password_hash=hashed,
                    display_name=display_name,
                    totp_secret=None,
                    totp_verified_at=None,
                    totp_required=False,
                    is_admin=is_admin,
                    is_active=True,
                ),
            )
            await session.commit()
            return "created"

        existing.password_hash = hashed
        existing.display_name = display_name or existing.display_name
        existing.totp_required = False
        existing.is_admin = is_admin
        existing.is_active = True
        await session.commit()
        return "updated"


async def reset_operator_password(*, email: str, password: str, set_admin: bool | None) -> str:
    """Update password only; fail if row missing; optionally patch ``is_admin``."""

    email_clean = email.strip().lower()
    hashed = hash_dashboard_password(password)

    async with async_session() as session:
        existing = await session.scalar(select(DashboardUser).where(DashboardUser.email == email_clean))
        if existing is None:
            print(f"bootstrap_dashboard_operator error: no user {email_clean!r}", file=sys.stderr)
            raise SystemExit(2)

        existing.password_hash = hashed
        existing.totp_required = False
        existing.is_active = True
        if set_admin is not None:
            existing.is_admin = set_admin
        await session.commit()
        return "password_reset"


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap one dashboard operator from env password.")
    parser.add_argument("--email", required=True, help="Operator email (unique).")
    parser.add_argument("--display-name", default="Hive Queen", help="Optional display label.")
    parser.add_argument("--admin", action="store_true", help="Grant dash admin scopes.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Only reset password (and disable TOTP requirement); user must already exist.",
    )
    args = parser.parse_args()

    secret = os.environ.get("QS_BOOTSTRAP_PASSWORD", "").strip()
    if not secret:
        print("bootstrap_dashboard_operator error: set QS_BOOTSTRAP_PASSWORD in the environment.", file=sys.stderr)
        sys.exit(1)
    if len(secret) < 8:
        print("bootstrap_dashboard_operator error: password too short (min 8).", file=sys.stderr)
        sys.exit(1)

    if args.reset:
        # --admin on reset: set admin True; omitting --admin leaves is_admin unchanged.
        set_admin: bool | None = True if args.admin else None
        action = asyncio.run(
            reset_operator_password(
                email=args.email,
                password=secret,
                set_admin=set_admin,
            ),
        )
        print(f"bootstrap_dashboard_operator {action} email={args.email!r}")
        return

    action = asyncio.run(
        upsert_operator(
            email=args.email,
            password=secret,
            display_name=args.display_name.strip() or None,
            is_admin=bool(args.admin),
        ),
    )
    print(f"bootstrap_dashboard_operator {action} email={args.email!r} admin={args.admin}")


if __name__ == "__main__":
    main()
