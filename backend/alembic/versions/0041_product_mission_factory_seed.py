"""Seed Product Mission factory recipe for revenue swarm playbook."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from app.domain.workflows.templates import PRODUCT_MISSION_WORKFLOW

revision = "0041_product_mission_factory_seed"
down_revision = "0040_premium_marketplace_seeds"
branch_labels = None
depends_on = None

_NAME = "Product Mission — Revenue Swarm"


def upgrade() -> None:
    conn = op.get_bind()
    existing = conn.execute(sa.text("SELECT id FROM recipes WHERE name = :n LIMIT 1"), {"n": _NAME}).fetchone()
    if existing is not None:
        return

    rid = uuid.uuid4()
    verified_at = datetime.now(tz=UTC)
    tags_json = json.dumps(["factory", "product", "monetize", "publish"])
    template_json = json.dumps(
        {"seed_key": "PRODUCT_MISSION", "steps": PRODUCT_MISSION_WORKFLOW.get("steps", [])},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO recipes (
              id, name, description, topic_tags, workflow_template,
              success_count, fail_count, avg_pollen_earned,
              embedding_id, created_by_agent_id, verified_at, last_used_at,
              is_deprecated, created_at, updated_at
            )
            VALUES (
              :id, :name, :description,
              CAST(:tags AS jsonb),
              CAST(:template AS jsonb),
              15, 1, 55.0,
              NULL, NULL,
              :verified_at, :verified_at,
              FALSE, NOW(), NOW()
            )
            """
        ),
        {
            "id": rid,
            "name": _NAME,
            "description": (
                "Ballroom playbook: niche → verified workflow → skill export → publish on GitHub, "
                "Gumroad, and optional Stripe."
            ),
            "tags": tags_json,
            "template": template_json,
            "verified_at": verified_at,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM recipes WHERE name = :n"), {"n": _NAME})
