"""Ensure ``alembic_version.version_num`` can store long revision filenames."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_alembic_version_widen"
down_revision = "0010_operator_external_apis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)"))
