"""Hive vectors in PostgreSQL via pgvector (single store; replaces Qdrant/Chroma containers)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_pgvector_hive_vectors"
down_revision = "0015_external_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable pgvector and create the shared embedding table + cosine HNSW index."""

    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS hive_vector_documents (
                id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                collection_name TEXT NOT NULL,
                document TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                embedding vector(384) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        ),
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS hive_vector_documents_collection_name_idx
            ON hive_vector_documents (collection_name)
            """
        ),
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS hive_vector_documents_embedding_hnsw_idx
            ON hive_vector_documents
            USING hnsw (embedding vector_cosine_ops)
            """
        ),
    )


def downgrade() -> None:
    """Drop the vector table; leave the extension installed (shared cluster safety)."""

    op.execute(sa.text("DROP TABLE IF EXISTS hive_vector_documents CASCADE"))
