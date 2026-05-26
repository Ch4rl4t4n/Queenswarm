#!/usr/bin/env python3
"""Bootstrap operator publish lane — Brain Pack + verified publish pack + queue approve.

Idempotent: skips brain seed when filled; reuses pending pack or skips if approved exists.
Safe for prod — simulate-only pack, no live API calls.

Usage (inside backend container):
  python scripts/seed_operator_publish_lane.py
  python scripts/seed_operator_publish_lane.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.publish_pack import (
    PublishPackArtifact,
    archive_verified_publish_pack,
)
from app.application.services.publish_queue import (
    build_publish_queue_snapshot,
    classify_publish_queue_status,
    review_publish_queue_item,
)
from app.application.services.social_publish import build_social_publish_snapshot
from app.application.services.social_publish import SOCIAL_OAUTH_CHANNEL_IDS
from app.application.services.tenancy import ensure_default_tenant_for_user
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession


def _pick_bootstrap_channel(channels: list) -> str:
    """Prefer connected social OAuth channel; default instagram for first live post docs."""

    social_rows = [
        row for row in channels if str(getattr(row, "channel", "")) in SOCIAL_OAUTH_CHANNEL_IDS
    ]
    for row in social_rows:
        if getattr(row, "active", False) and getattr(row, "credentials_ok", False):
            return str(getattr(row, "channel", "instagram"))
    for row in social_rows:
        if getattr(row, "installed", False):
            return str(getattr(row, "channel", "instagram"))
    return "instagram"


def _is_social_channel(channel: str) -> bool:
    return channel in SOCIAL_OAUTH_CHANNEL_IDS


async def seed_operator_publish_lane(
    *,
    email: str | None = None,
    seed_brain: bool = True,
    overwrite_brain: bool = False,
    auto_approve: bool = True,
) -> dict[str, object]:
    """Seed Brain Pack and one approved simulate-only publish pack for the operator."""

    load_all_models()
    async with async_session() as session:
        stmt = select(DashboardUser).where(DashboardUser.is_active.is_(True))
        if email:
            stmt = stmt.where(DashboardUser.email == email.strip().lower())
        else:
            stmt = stmt.where(DashboardUser.is_admin.is_(True))
        user = await session.scalar(stmt.order_by(DashboardUser.created_at.asc()).limit(1))
        if user is None:
            user = await session.scalar(
                select(DashboardUser)
                .where(DashboardUser.is_active.is_(True))
                .order_by(DashboardUser.created_at.asc())
                .limit(1),
            )
        if user is None:
            raise RuntimeError("No active dashboard user — run bootstrap_dashboard_operator first.")

        tenant = await ensure_default_tenant_for_user(session, user=user)
        result: dict[str, object] = {
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "brain_seeded": [],
            "brain_skipped": [],
            "deliverable_id": None,
            "approved": False,
            "channel": "instagram",
            "action": "noop",
        }

        if seed_brain:
            memory = CuratedMemoryService(db=session)
            seeded, skipped = await memory.seed_starter_pack(
                tenant.id,
                user_id=user.id,
                overwrite=overwrite_brain,
            )
            result["brain_seeded"] = list(seeded)
            result["brain_skipped"] = list(skipped)

        queue = await build_publish_queue_snapshot(session, dashboard_user_id=user.id)
        social_approved = [
            item for item in queue.items if item.status == "approved" and _is_social_channel(item.channel)
        ]
        if social_approved:
            item = social_approved[0]
            result["deliverable_id"] = str(item.id)
            result["approved"] = True
            result["channel"] = item.channel
            result["action"] = "existing_approved"
            await session.commit()
            return result

        if queue.approved_count > 0:
            result["action"] = "recreate_social_pack"

        pending = next(
            (item for item in queue.items if item.status == "pending" and _is_social_channel(item.channel)),
            None,
        )
        if pending is not None and auto_approve:
            reviewed = await review_publish_queue_item(
                session,
                deliverable_id=pending.id,
                dashboard_user_id=user.id,
                decision="approve",
                note="operator publish lane bootstrap",
                reviewed_by=f"dashboard:{user.id}",
            )
            result["deliverable_id"] = str(reviewed.id)
            result["approved"] = True
            result["channel"] = pending.channel
            result["action"] = "approved_pending"
            await session.commit()
            return result

        social = await build_social_publish_snapshot(
            session,
            dashboard_user_id=user.id,
            tenant=tenant,
            limit=5,
        )
        channel = _pick_bootstrap_channel(social.channels)
        result["channel"] = channel

        supervisor = SupervisorSession(
            tenant_id=tenant.id,
            goal="Operator publish lane bootstrap — simulate demo pack",
            status="completed",
            runtime_mode="inprocess",
            created_by_subject=f"dashboard:{user.id}",
            context_summary={"bootstrap": "operator_publish_lane", "channel": channel},
            started_at=datetime.now(tz=UTC),
            completed_at=datetime.now(tz=UTC),
        )
        session.add(supervisor)
        await session.flush()

        pack = PublishPackArtifact(
            channel=channel,  # type: ignore[arg-type]
            title="Queenswarm operator simulate demo",
            body=(
                "Hello from Queenswarm — simulate-only publish lane check. "
                "Approve → Social Simulate → enable live when OAuth is ready."
            ),
            hashtags=["Queenswarm", "SimulateOnly"],
            cta="Learn more at queenswarm.love",
            simulate_only=True,
            media_url="https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png",
        )
        row = await archive_verified_publish_pack(
            session,
            supervisor_session=supervisor,
            pack=pack,
            critic_excerpt="Bootstrap verified — operator simulate gate.",
            verified=True,
        )
        if row is None:
            raise RuntimeError("Failed to archive publish pack.")

        result["deliverable_id"] = str(row.id)
        result["action"] = "created"

        if auto_approve:
            if classify_publish_queue_status(row) != "pending":
                msg = "Archived pack is not pending for queue review."
                raise RuntimeError(msg)
            reviewed = await review_publish_queue_item(
                session,
                deliverable_id=row.id,
                dashboard_user_id=user.id,
                decision="approve",
                note="operator publish lane bootstrap",
                reviewed_by=f"dashboard:{user.id}",
            )
            result["approved"] = reviewed.status == "approved"
        else:
            result["approved"] = False

        await session.commit()
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed operator Brain Pack + approved publish pack.")
    parser.add_argument("--email", default=None, help="Dashboard user email (default: first admin).")
    parser.add_argument("--no-brain", action="store_true", help="Skip Brain Pack starter seed.")
    parser.add_argument("--overwrite-brain", action="store_true", help="Overwrite all Brain Pack slots.")
    parser.add_argument("--no-approve", action="store_true", help="Create pack but leave queue pending.")
    parser.add_argument("--json", action="store_true", help="Print JSON result only.")
    args = parser.parse_args()

    payload = asyncio.run(
        seed_operator_publish_lane(
            email=args.email,
            seed_brain=not args.no_brain,
            overwrite_brain=args.overwrite_brain,
            auto_approve=not args.no_approve,
        ),
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"publish_lane action={payload['action']} "
            f"deliverable_id={payload['deliverable_id']} "
            f"approved={payload['approved']} channel={payload['channel']}",
        )
        if payload.get("brain_seeded"):
            print(f"brain_seeded={payload['brain_seeded']}")


if __name__ == "__main__":
    main()
