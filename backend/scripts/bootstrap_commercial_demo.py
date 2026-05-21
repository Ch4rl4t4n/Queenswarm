#!/usr/bin/env python3
"""Bootstrap a commercial demo tenant + non-admin user for customer-surface testing.

Requires env ``QS_BOOTSTRAP_PASSWORD`` (min 8 chars) unless ``--password`` is passed.
Idempotent — safe to re-run.
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

from app.application.services.admin_accounts import (
    COMMERCIAL_DEMO_DISPLAY,
    COMMERCIAL_DEMO_EMAIL,
    COMMERCIAL_DEMO_TENANT_NAME,
    COMMERCIAL_DEMO_TENANT_SLUG,
    ensure_commercial_demo_account,
    mint_bootstrap_password,
)
from app.application.services.billing import TIER_PRO
from app.core.database import async_session


async def bootstrap_commercial_demo(
    *,
    email: str,
    password: str,
    display_name: str,
    tenant_slug: str,
    tenant_name: str,
    tier: str,
) -> None:
    """Create or refresh commercial demo tenant, user, membership, and subscription."""

    async with async_session() as session:
        result = await ensure_commercial_demo_account(
            session,
            email=email,
            password=password,
            display_name=display_name,
            tenant_slug=tenant_slug,
            tenant_name=tenant_name,
            tier=tier,
            actor_user_id=None,
        )
        await session.commit()
        print(
            f"commercial_demo ready tenant_id={result['tenant_id']} user_id={result['user_id']} "
            f"tier={result['tier']} platform_mode={result['platform_mode']}",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap commercial demo tenant + user.")
    parser.add_argument("--email", default=COMMERCIAL_DEMO_EMAIL, help="Demo user email.")
    parser.add_argument("--display-name", default=COMMERCIAL_DEMO_DISPLAY, help="Demo display name.")
    parser.add_argument("--tenant-slug", default=COMMERCIAL_DEMO_TENANT_SLUG, help="Demo tenant slug.")
    parser.add_argument("--tenant-name", default=COMMERCIAL_DEMO_TENANT_NAME, help="Demo tenant label.")
    parser.add_argument("--tier", default=TIER_PRO, choices=["free", "pro", "enterprise"], help="Subscription tier.")
    parser.add_argument("--password", default="", help="Override QS_BOOTSTRAP_PASSWORD.")
    args = parser.parse_args()

    try:
        secret = mint_bootstrap_password(
            env_password=(args.password or os.environ.get("QS_BOOTSTRAP_PASSWORD", "")).strip(),
        )
    except ValueError as exc:
        print(f"bootstrap_commercial_demo error: {exc}", file=sys.stderr)
        if not (args.password or os.environ.get("QS_BOOTSTRAP_PASSWORD", "")).strip():
            print("Set QS_BOOTSTRAP_PASSWORD in the environment or pass --password.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(
        bootstrap_commercial_demo(
            email=args.email,
            password=secret,
            display_name=args.display_name.strip() or COMMERCIAL_DEMO_DISPLAY,
            tenant_slug=args.tenant_slug.strip(),
            tenant_name=args.tenant_name.strip(),
            tier=args.tier.strip().lower(),
        ),
    )


if __name__ == "__main__":
    main()
