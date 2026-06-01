"""Raise curated_memory char_count ceiling to 24000 (operational default 16000 via settings)."""

from __future__ import annotations

from alembic import op

revision = "0055_curated_memory_char_limit_24k"
down_revision = "0054_intel_source_cursors"
branch_labels = None
depends_on = None

_DB_CHAR_CEILING = 24_000


def upgrade() -> None:
    """Allow larger curated memory files — config default remains 16000."""

    op.drop_constraint("ck_curated_memory_char_count_max", "curated_memory", type_="check")
    op.create_check_constraint(
        "ck_curated_memory_char_count_max",
        "curated_memory",
        f"char_count <= {_DB_CHAR_CEILING}",
    )


def downgrade() -> None:
    """Restore legacy 8000 char ceiling."""

    op.drop_constraint("ck_curated_memory_char_count_max", "curated_memory", type_="check")
    op.create_check_constraint(
        "ck_curated_memory_char_count_max",
        "curated_memory",
        "char_count <= 8000",
    )
