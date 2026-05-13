"""Seed the fixed Orchestrator bee + its universal config."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0006_seed_orchestrator"
down_revision = "0005_agent_configs"
branch_labels = None
depends_on = None

_ORCH_NAME = "Orchestrator"
_ORCH_SYSTEM_PROMPT = (
    "You coordinate hive managers and workers on queenswarm.love. Interpret user goals, delegate "
    "to the right specialists, and return concise verified outcomes."
)


def upgrade() -> None:
    """Insert Orchestrator agent row when missing (idempotent by unique name)."""

    conn = op.get_bind()
    existing = conn.execute(sa.text("SELECT id FROM agents WHERE name = :n LIMIT 1"), {"n": _ORCH_NAME}).fetchone()
    if existing is not None:
        return

    aid = uuid.uuid4()
    cid = uuid.uuid4()
    agent_cfg_obj = '{"hive_fixed": true, "hive_tier": "orchestrator"}'
    oc_obj = '{"hive_tier": "orchestrator"}'

    conn.execute(
        sa.text(
            """
            INSERT INTO agents (
              id, name, role, status, swarm_id, config, pollen_points, performance_score,
              created_at, updated_at
            )
            VALUES (
              :id, :name, 'learner', 'idle', NULL,
              CAST(:cfg AS jsonb),
              0.0, 0.0,
              NOW(), NOW()
            )
            """
        ),
        {"id": aid, "name": _ORCH_NAME, "cfg": agent_cfg_obj},
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO agent_configs (
              id, created_at, updated_at, agent_id, system_prompt,
              user_prompt_template, tools, output_format, output_destination,
              output_config, schedule_type, schedule_value, is_active,
              last_run_at, last_run_result, run_count
            )
            VALUES (
              :cid, NOW(), NOW(), :aid, :sys,
              NULL, '[]'::jsonb, 'text', 'ballroom',
              CAST(:oc AS jsonb),
              'on_demand', NULL, TRUE,
              NULL, NULL, 0
            )
            """
        ),
        {"cid": cid, "aid": aid, "sys": _ORCH_SYSTEM_PROMPT, "oc": oc_obj},
    )


def downgrade() -> None:
    """Remove seeded Orchestrator (cascades ``agent_configs`` via FK)."""

    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM agents WHERE name = :n"), {"n": _ORCH_NAME})
