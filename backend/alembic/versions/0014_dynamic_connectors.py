"""Dynamic Connector Hub catalog (Phase 1.2)."""

from __future__ import annotations

import json
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_dynamic_connectors"
down_revision = "0013_task_final_deliverables"
branch_labels = None
depends_on = None


_GROKIPEDIA_MANIFEST: dict[str, object] = {
    "tools": [
        {
            "name": "article_fetch",
            "description": "Fetch Grokipedia article body as cleaned text (Wikipedia successor lane).",
            "path": "/wiki/{slug}",
            "method": "GET",
        }
    ]
}


def upgrade() -> None:
    op.create_table(
        "dynamic_connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("auth_type", sa.String(length=32), nullable=False),
        sa.Column("secrets_cipher", sa.Text(), nullable=True),
        sa.Column("mcp_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "allowed_manager_slugs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("builtin_kind", sa.String(length=64), nullable=True),
        sa.Column(
            "last_tested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("dashboard_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["dashboard_user_id"],
            ["dashboard_users.id"],
            name="fk_dynamic_connectors_dashboard_user_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_dynamic_connectors_slug"),
    )
    op.create_index("ix_dynamic_connectors_slug", "dynamic_connectors", ["slug"], unique=False)
    op.create_index(
        "ix_dynamic_connectors_is_active_idx",
        "dynamic_connectors",
        ["is_active"],
        unique=False,
    )

    seeded = uuid.UUID("00000000-0000-4000-a000-000000000071")
    manifest_txt = json.dumps(_GROKIPEDIA_MANIFEST)
    managers_txt = json.dumps(["research_intelligence"])
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO dynamic_connectors (
                id,
                slug,
                display_name,
                base_url,
                auth_type,
                secrets_cipher,
                mcp_manifest,
                allowed_manager_slugs,
                is_active,
                is_builtin,
                builtin_kind,
                last_tested_at,
                dashboard_user_id
            ) VALUES (
                CAST(:dc_id AS uuid),
                :slug,
                :display_name,
                :base_url,
                :auth_type,
                NULL,
                CAST(:manifest AS jsonb),
                CAST(:managers AS jsonb),
                TRUE,
                TRUE,
                :builtin_kind,
                NULL,
                NULL
            )
            """,
        ),
        {
            "dc_id": str(seeded),
            "slug": "grokipedia",
            "display_name": "Grokipedia (built-in)",
            "base_url": "https://grokipedia.org",
            "auth_type": "none",
            "manifest": manifest_txt,
            "managers": managers_txt,
            "builtin_kind": "grokipedia",
        },
    )


def downgrade() -> None:
    op.drop_index("ix_dynamic_connectors_is_active_idx", table_name="dynamic_connectors")
    op.drop_index("ix_dynamic_connectors_slug", table_name="dynamic_connectors")
    op.drop_table("dynamic_connectors")
