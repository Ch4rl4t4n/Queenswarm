"""Paper trading accounts + fill ledger."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0037_paper_trading_ledger"
down_revision = "0036_verified_pollen_skill_purchases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_trading_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_usd", sa.Numeric(16, 4), nullable=False, server_default="10000"),
        sa.Column("starting_cash_usd", sa.Numeric(16, 4), nullable=False, server_default="10000"),
        sa.Column("realized_pnl_usd", sa.Numeric(16, 4), nullable=False, server_default="0"),
        sa.Column("daily_realized_pnl_usd", sa.Numeric(16, 4), nullable=False, server_default="0"),
        sa.Column("daily_pnl_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_halted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("halt_reason", sa.String(length=500), nullable=True),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "watchlist",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[\"BTC\",\"ETH\"]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["external_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_paper_trading_accounts_project_id"),
    )
    op.create_index("ix_paper_trading_accounts_project_id", "paper_trading_accounts", ["project_id"], unique=False)
    op.create_index("ix_paper_trading_accounts_tenant_id", "paper_trading_accounts", ["tenant_id"], unique=False)

    op.create_table(
        "paper_trading_fills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("fill_price_usd", sa.Numeric(16, 4), nullable=False),
        sa.Column("fees_usd", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("notional_usd", sa.Numeric(16, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("signal_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["paper_trading_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["external_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_trading_fills_project_id", "paper_trading_fills", ["project_id"], unique=False)
    op.create_index("ix_paper_trading_fills_account_id", "paper_trading_fills", ["account_id"], unique=False)
    op.create_index("ix_paper_trading_fills_symbol", "paper_trading_fills", ["symbol"], unique=False)
    op.create_index("ix_paper_trading_fills_created_at", "paper_trading_fills", ["created_at"], unique=False)
    op.create_index("ix_paper_trading_fills_tenant_id", "paper_trading_fills", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_paper_trading_fills_tenant_id", table_name="paper_trading_fills")
    op.drop_index("ix_paper_trading_fills_created_at", table_name="paper_trading_fills")
    op.drop_index("ix_paper_trading_fills_symbol", table_name="paper_trading_fills")
    op.drop_index("ix_paper_trading_fills_account_id", table_name="paper_trading_fills")
    op.drop_index("ix_paper_trading_fills_project_id", table_name="paper_trading_fills")
    op.drop_table("paper_trading_fills")
    op.drop_index("ix_paper_trading_accounts_tenant_id", table_name="paper_trading_accounts")
    op.drop_index("ix_paper_trading_accounts_project_id", table_name="paper_trading_accounts")
    op.drop_table("paper_trading_accounts")
