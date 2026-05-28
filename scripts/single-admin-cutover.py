#!/usr/bin/env python3
"""Destructive single-admin hard cutover utility."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.application.services.single_admin_mode import (  # noqa: E402
    SingleAdminInvariantError,
    run_single_admin_hard_cutover,
)
from app.core.database import async_session  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Hard-delete all non-primary tenants/users and keep one admin identity. "
            "Use --apply to execute; default mode is dry-run."
        ),
    )
    parser.add_argument(
        "--admin-email",
        required=True,
        help="Keeper dashboard admin email (exact row to preserve).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute destructive cutover (without this flag, tool runs dry-run).",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    async with async_session() as session:
        try:
            payload = await run_single_admin_hard_cutover(
                session,
                admin_email=args.admin_email,
                dry_run=not args.apply,
            )
            if args.apply:
                await session.commit()
            else:
                await session.rollback()
        except SingleAdminInvariantError as exc:
            await session.rollback()
            print(f"single-admin-cutover: FAILED: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            print(f"single-admin-cutover: UNEXPECTED: {exc}", file=sys.stderr)
            return 3

    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.apply:
        print("single-admin-cutover: APPLY completed")
    else:
        print("single-admin-cutover: dry-run completed (no changes committed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))

