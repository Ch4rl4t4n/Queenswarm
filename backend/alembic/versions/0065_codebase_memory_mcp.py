"""Seed builtin codebase-memory MCP connector — POS-I5 / H7."""

from __future__ import annotations

import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0065_codebase_memory_mcp"
down_revision = "0064_tenant_finetune_jobs"
branch_labels = None
depends_on = None

_MANIFEST: dict[str, object] = {
    "tools": [
        {
            "name": "search_hive_mind",
            "description": "Semantic search HiveMind embeddings for Tech SCV / maintainer context.",
            "path": "/search",
            "method": "POST",
            "allowed_manager_slugs": [
                "execution_operations",
                "review_quality",
                "research_intelligence",
            ],
        },
        {
            "name": "tech_health_snapshot",
            "description": "Read-only repo tech health signals (deps, maintainer docs, perf tests).",
            "path": "/tech-health",
            "method": "GET",
            "allowed_manager_slugs": [
                "execution_operations",
                "review_quality",
                "research_intelligence",
            ],
        },
    ],
}


def upgrade() -> None:
    seeded = uuid.UUID("00000000-0000-4000-a000-000000000072")
    manifest_txt = json.dumps(_MANIFEST)
    managers_txt = json.dumps(
        ["execution_operations", "review_quality", "research_intelligence"],
    )
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT 1 FROM dynamic_connectors WHERE slug = :slug LIMIT 1"),
        {"slug": "codebase_memory"},
    ).scalar()
    if exists:
        return
    bind.execute(
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
            "slug": "codebase_memory",
            "display_name": "Codebase Memory MCP",
            "base_url": "internal://codebase-memory",
            "auth_type": "none",
            "manifest": manifest_txt,
            "managers": managers_txt,
            "builtin_kind": "codebase_memory",
        },
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM dynamic_connectors WHERE slug = 'codebase_memory' AND is_builtin = TRUE"),
    )
