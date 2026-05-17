"""Merge supervisor and curated memory Alembic heads."""

from __future__ import annotations

revision = "0029_merge_heads"
down_revision = ("0018_supervisor_routines", "0028_add_curated_memory")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge heads only; no schema operation required."""

    return


def downgrade() -> None:
    """Unmerge heads by stepping back this no-op revision."""

    return
