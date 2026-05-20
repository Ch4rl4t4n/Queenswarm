"""Seed verified premium recipes for skills export marketplace."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from app.domain.workflows.templates import SEED_WORKFLOWS

revision = "0040_premium_marketplace_seeds"
down_revision = "0039_hive_stripe_secrets"
branch_labels = None
depends_on = None

_SEEDS: tuple[dict[str, object], ...] = (
    {
        "name": "Premium — Crypto Sentiment Swarm",
        "description": (
            "Verified 4-step swarm: scrape YouTube crypto sentiment, evaluate claims, "
            "simulate portfolio paths, export trading memo. Simulation-gated export bundle."
        ),
        "topic_tags": ["premium", "crypto", "trading", "simulation"],
        "seed_key": "CRYPTO_ACKIE",
        "success_count": 12,
        "fail_count": 2,
        "avg_pollen_earned": 48.0,
    },
    {
        "name": "Premium — Blog Launch Pipeline",
        "description": (
            "Research clusters → outline → draft → publish checklist. Battle-tested content "
            "workflow exported as Cursor/Claude SKILL.md + HIVE.md."
        ),
        "topic_tags": ["premium-29", "content", "blog", "seo"],
        "seed_key": "BLOG_POST",
        "success_count": 9,
        "fail_count": 1,
        "avg_pollen_earned": 36.0,
    },
    {
        "name": "Premium — Newsletter Growth Loop",
        "description": (
            "Audience scrape, CAN-SPAM compliance pass, subject-line simulation. "
            "One-time unlock for verified newsletter automation recipe."
        ),
        "topic_tags": ["premium-9", "newsletter", "email", "growth"],
        "seed_key": "NEWSLETTER",
        "success_count": 7,
        "fail_count": 0,
        "avg_pollen_earned": 22.0,
    },
)


def upgrade() -> None:
    """Insert verified premium marketplace recipes when missing."""

    conn = op.get_bind()
    verified_at = datetime.now(tz=UTC)
    for spec in _SEEDS:
        name = str(spec["name"])
        existing = conn.execute(
            sa.text("SELECT id FROM recipes WHERE name = :n LIMIT 1"),
            {"n": name},
        ).fetchone()
        if existing is not None:
            continue

        rid = uuid.uuid4()
        tags_json = json.dumps(list(spec["topic_tags"]))
        seed_key = str(spec["seed_key"])
        blob = SEED_WORKFLOWS.get(seed_key, {})
        template_json = json.dumps({"seed_key": seed_key, "steps": blob.get("steps", [])})
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
                "id": rid,
                "name": name,
                "description": str(spec["description"]),
                "tags": tags_json,
                "template": template_json,
                "success_count": int(spec["success_count"]),  # type: ignore[arg-type]
                "fail_count": int(spec["fail_count"]),  # type: ignore[arg-type]
                "avg_pollen": float(spec["avg_pollen_earned"]),  # type: ignore[arg-type]
                "verified_at": verified_at,
            },
        )


def downgrade() -> None:
    """Remove seeded premium marketplace recipes."""

    conn = op.get_bind()
    for spec in _SEEDS:
        conn.execute(sa.text("DELETE FROM recipes WHERE name = :n"), {"n": str(spec["name"])})
