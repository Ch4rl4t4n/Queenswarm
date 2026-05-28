"""Neutralize legacy billing schema names and drop unused secret vault."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0051_billing_schema_neutralization"
down_revision = "0050_grok_control_plane"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    tables = _table_names()

    if "tenant_subscriptions" in tables:
        columns = _column_names("tenant_subscriptions")
        if "stripe_customer_id" in columns and "billing_customer_id" not in columns:
            op.alter_column(
                "tenant_subscriptions",
                "stripe_customer_id",
                new_column_name="billing_customer_id",
                existing_type=sa.String(length=128),
                existing_nullable=True,
            )
        if "stripe_subscription_id" in columns and "billing_subscription_id" not in columns:
            op.alter_column(
                "tenant_subscriptions",
                "stripe_subscription_id",
                new_column_name="billing_subscription_id",
                existing_type=sa.String(length=128),
                existing_nullable=True,
            )
        op.execute(sa.text("DROP INDEX IF EXISTS ix_tenant_subscriptions_stripe_customer_id"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_tenant_subscriptions_stripe_subscription_id"))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_tenant_subscriptions_billing_customer_id ON tenant_subscriptions (billing_customer_id)"))
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_tenant_subscriptions_billing_subscription_id "
                "ON tenant_subscriptions (billing_subscription_id)"
            )
        )

    if "skill_purchases" in tables:
        columns = _column_names("skill_purchases")
        if "stripe_checkout_session_id" in columns and "checkout_session_id" not in columns:
            op.alter_column(
                "skill_purchases",
                "stripe_checkout_session_id",
                new_column_name="checkout_session_id",
                existing_type=sa.String(length=255),
                existing_nullable=True,
            )
        if "stripe_payment_intent_id" in columns and "payment_intent_id" not in columns:
            op.alter_column(
                "skill_purchases",
                "stripe_payment_intent_id",
                new_column_name="payment_intent_id",
                existing_type=sa.String(length=255),
                existing_nullable=True,
            )
        op.execute(sa.text("DROP INDEX IF EXISTS ix_skill_purchases_stripe_checkout_session_id"))
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_skill_purchases_checkout_session_id "
                "ON skill_purchases (checkout_session_id)"
            )
        )

    if "hive_stripe_secrets" in tables:
        op.drop_table("hive_stripe_secrets")


def downgrade() -> None:
    tables = _table_names()

    if "tenant_subscriptions" in tables:
        columns = _column_names("tenant_subscriptions")
        if "billing_customer_id" in columns and "stripe_customer_id" not in columns:
            op.alter_column(
                "tenant_subscriptions",
                "billing_customer_id",
                new_column_name="stripe_customer_id",
                existing_type=sa.String(length=128),
                existing_nullable=True,
            )
        if "billing_subscription_id" in columns and "stripe_subscription_id" not in columns:
            op.alter_column(
                "tenant_subscriptions",
                "billing_subscription_id",
                new_column_name="stripe_subscription_id",
                existing_type=sa.String(length=128),
                existing_nullable=True,
            )
        op.execute(sa.text("DROP INDEX IF EXISTS ix_tenant_subscriptions_billing_customer_id"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_tenant_subscriptions_billing_subscription_id"))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_tenant_subscriptions_stripe_customer_id ON tenant_subscriptions (stripe_customer_id)"))
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_tenant_subscriptions_stripe_subscription_id "
                "ON tenant_subscriptions (stripe_subscription_id)"
            )
        )

    if "skill_purchases" in tables:
        columns = _column_names("skill_purchases")
        if "checkout_session_id" in columns and "stripe_checkout_session_id" not in columns:
            op.alter_column(
                "skill_purchases",
                "checkout_session_id",
                new_column_name="stripe_checkout_session_id",
                existing_type=sa.String(length=255),
                existing_nullable=True,
            )
        if "payment_intent_id" in columns and "stripe_payment_intent_id" not in columns:
            op.alter_column(
                "skill_purchases",
                "payment_intent_id",
                new_column_name="stripe_payment_intent_id",
                existing_type=sa.String(length=255),
                existing_nullable=True,
            )
        op.execute(sa.text("DROP INDEX IF EXISTS ix_skill_purchases_checkout_session_id"))
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_skill_purchases_stripe_checkout_session_id "
                "ON skill_purchases (stripe_checkout_session_id)"
            )
        )

    if "hive_stripe_secrets" not in tables:
        op.create_table(
            "hive_stripe_secrets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("secret_key_ciphertext", sa.Text(), nullable=True),
            sa.Column("webhook_secret_ciphertext", sa.Text(), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
