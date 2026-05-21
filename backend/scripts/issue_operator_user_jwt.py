#!/usr/bin/env python3
"""Emit a dashboard user access JWT for operator walkthrough smoke (prints token only)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.application.services.tenancy import ensure_default_tenant_for_user
from app.core.database import async_session
from app.core.jwt_tokens import create_dashboard_access_token
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.dashboard_user import DashboardUser


def _scopes_for(user: DashboardUser) -> str:
    """Mirror dashboard login scopes for walkthrough probes."""

    bits = ["dash:read", "dash:operator"]
    if user.is_admin:
        bits.extend(["dash:admin", "dash:recipe_write"])
    return " ".join(sorted(set(bits)))


async def mint_operator_user_jwt(*, email: str | None = None) -> str:
    """Resolve an active dashboard user and mint a tenant-scoped access token."""

    load_all_models()
    async with async_session() as session:
        stmt = select(DashboardUser).where(DashboardUser.is_active.is_(True))
        if email:
            stmt = stmt.where(DashboardUser.email == email.strip().lower())
        else:
            stmt = stmt.where(DashboardUser.is_admin.is_(True))
        user = await session.scalar(stmt.order_by(DashboardUser.created_at.asc()).limit(1))
        if user is None and email is None:
            user = await session.scalar(
                select(DashboardUser)
                .where(DashboardUser.is_active.is_(True))
                .order_by(DashboardUser.created_at.asc())
                .limit(1),
            )
        if user is None:
            raise RuntimeError("No active dashboard user found — run dashboard_seed or bootstrap_dashboard_operator.")

        tenant = await ensure_default_tenant_for_user(session, user=user)
        token, _ttl = create_dashboard_access_token(
            user_id=user.id,
            email=user.email,
            scopes=_scopes_for(user),
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
        )
        return token


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Mint operator user JWT for prod walkthrough gate.")
    parser.add_argument("--email", default=None, help="Optional dashboard user email (default: first admin).")
    args = parser.parse_args()
    print(asyncio.run(mint_operator_user_jwt(email=args.email)))


if __name__ == "__main__":
    main()
