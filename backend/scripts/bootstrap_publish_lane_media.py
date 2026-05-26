#!/usr/bin/env python3
"""Patch approved publish packs missing media_url (onboarding publish_media step)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.application.services.publish_queue import build_publish_queue_snapshot
from app.core.database import async_session
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

DEFAULT_MEDIA_URL = "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"


async def patch_publish_media(*, email: str | None, media_url: str) -> dict[str, object]:
    async with async_session() as db:
        stmt = select(DashboardUser).where(DashboardUser.is_active.is_(True))
        if email:
            stmt = stmt.where(DashboardUser.email == email.strip().lower())
        else:
            stmt = stmt.where(DashboardUser.is_admin.is_(True))
        user = await db.scalar(stmt.order_by(DashboardUser.created_at.asc()).limit(1))
        if user is None:
            raise SystemExit("No dashboard user found.")

        queue = await build_publish_queue_snapshot(db, dashboard_user_id=user.id)
        patched: list[str] = []
        for item in queue.items:
            if item.status != "approved" or item.media_url:
                continue
            row = await db.get(TaskFinalDeliverable, item.id)
            if row is None:
                continue
            structured = dict(row.structured_json or {})
            structured["media_url"] = media_url
            structured["media_kind"] = "image"
            row.structured_json = structured
            patched.append(str(row.id))

        await db.commit()
        return {"patched_count": len(patched), "patched_ids": patched, "media_url": media_url}


def main() -> None:
    parser = argparse.ArgumentParser(description="Add media_url to approved publish packs.")
    parser.add_argument("--email", default=None)
    parser.add_argument("--media-url", default=DEFAULT_MEDIA_URL)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = asyncio.run(patch_publish_media(email=args.email, media_url=args.media_url.strip()))
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"patched={payload['patched_count']} media_url={payload['media_url']}")


if __name__ == "__main__":
    main()
