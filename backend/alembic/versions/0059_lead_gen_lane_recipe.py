"""Seed verified Lead Gen Lane recipe."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from app.domain.workflows.templates import SEED_WORKFLOWS

revision = "0059_lead_gen_lane_recipe"
down_revision = "0058_wiki_layer"
branch_labels = None
depends_on = None

_SEED: dict[str, object] = {
    "name": "Verified — Lead Gen Lane",
    "description": (
        "5-step simulate-first pipeline: ICP brief → Lead Scout (≤10) → optional intel → "
        "Outreach Draft (≤5, Gmail simulate) → critic report. No live send."
    ),
    "topic_tags": ["lead-gen", "outreach", "sales", "verified", "simulate"],
    "seed_key": "LEAD_GEN_LANE",
    "success_count": 6,
    "fail_count": 0,
    "avg_pollen_earned": 28.0,
}


def upgrade() -> None:
    """Insert verified Lead Gen Lane recipe when missing."""

    conn = op.get_bind()
    name = str(_SEED["name"])
    existing = conn.execute(
        sa.text("SELECT id FROM recipes WHERE name = :n LIMIT 1"),
        {"n": name},
    ).fetchone()
    if existing is not None:
        return

    seed_key = str(_SEED["seed_key"])
    blob = SEED_WORKFLOWS.get(seed_key, {})
    verified_at = datetime.now(tz=UTC)
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
              :success_count, :fail_count, :avg_pollen,
              NULL, NULL,
              :verified_at,
              :verified_at,
              FALSE, NOW(), NOW()
            )
            """
        ),
        {
            "id": uuid.uuid4(),
            "name": name,
            "description": str(_SEED["description"]),
            "tags": json.dumps(list(_SEED["topic_tags"])),
            "template": json.dumps({"seed_key": seed_key, "steps": blob.get("steps", [])}),
            "success_count": int(_SEED["success_count"]),  # type: ignore[arg-type]
            "fail_count": int(_SEED["fail_count"]),  # type: ignore[arg-type]
            "avg_pollen": float(_SEED["avg_pollen_earned"]),  # type: ignore[arg-type]
            "verified_at": verified_at,
        },
    )


def downgrade() -> None:
    """Remove seeded Lead Gen Lane recipe."""

    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM recipes WHERE name = :n"),
        {"n": str(_SEED["name"])},
    )
