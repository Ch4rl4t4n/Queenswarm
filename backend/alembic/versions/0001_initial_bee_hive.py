"""Initial bee-hive relational schema (Global Hive Mind Postgres tier)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "0001_initial_bee_hive"
down_revision = None
branch_labels = None
depends_on = None

UUID = pg.UUID(as_uuid=True)


def upgrade() -> None:
    """Provision core tables, foreign keys, and JSONB GIN indexes."""

    jsonb_obj = sa.text("'{}'::jsonb")
    jsonb_arr = sa.text("'[]'::jsonb")

    op.create_table(
        "sub_swarms",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column(
            "local_memory",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_obj,
            nullable=False,
        ),
        sa.Column("queen_agent_id", UUID, nullable=True),
        sa.Column("last_global_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_pollen", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("member_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("name", name="uq_sub_swarms_name"),
    )

    op.create_table(
        "agents",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="idle", nullable=False),
        sa.Column("swarm_id", UUID, nullable=True),
        sa.Column(
            "config",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_obj,
            nullable=False,
        ),
        sa.Column("pollen_points", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("performance_score", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["swarm_id"],
            ["sub_swarms.id"],
            name="fk_agents_swarm_id_sub_swarms",
        ),
        sa.UniqueConstraint("name", name="uq_agents_name"),
    )
    op.create_index("ix_agents_swarm_id", "agents", ["swarm_id"], unique=False)

    op.create_foreign_key(
        "fk_sub_swarms_queen_agent_id",
        "sub_swarms",
        "agents",
        ["queen_agent_id"],
        ["id"],
    )

    op.create_table(
        "recipes",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "topic_tags",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_arr,
            nullable=False,
        ),
        sa.Column("workflow_template", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("success_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fail_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "avg_pollen_earned",
            sa.Float(),
            server_default=sa.text("0.0"),
            nullable=False,
        ),
        sa.Column("embedding_id", sa.String(length=160), nullable=True),
        sa.Column("created_by_agent_id", UUID, nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deprecated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_agent_id"],
            ["agents.id"],
            name="fk_recipes_created_by_agent_id",
        ),
        sa.UniqueConstraint("name", name="uq_recipes_name"),
    )
    op.create_index(
        "ix_recipes_topic_tags_gin",
        "recipes",
        ["topic_tags"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_table(
        "workflows",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("original_task_text", sa.Text(), nullable=False),
        sa.Column("decomposition_rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("total_steps", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_steps", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "parallelizable_groups",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_arr,
            nullable=False,
        ),
        sa.Column("matching_recipe_id", UUID, nullable=True),
        sa.Column("estimated_duration_sec", sa.Integer(), nullable=True),
        sa.Column("actual_duration_sec", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["matching_recipe_id"],
            ["recipes.id"],
            name="fk_workflows_matching_recipe_id",
        ),
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("workflow_id", UUID, nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("agent_role", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column(
            "input_schema",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_obj,
            nullable=False,
        ),
        sa.Column(
            "output_schema",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_obj,
            nullable=False,
        ),
        sa.Column(
            "guardrails",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_obj,
            nullable=False,
        ),
        sa.Column(
            "evaluation_criteria",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_obj,
            nullable=False,
        ),
        sa.Column("result", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            ondelete="CASCADE",
            name="fk_workflow_steps_workflow_id",
        ),
    )
    op.create_index(
        "ix_workflow_steps_workflow_id",
        "workflow_steps",
        ["workflow_id"],
        unique=False,
    )

    op.create_table(
        "tasks",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("task_type", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="5", nullable=False),
        sa.Column(
            "payload",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_obj,
            nullable=False,
        ),
        sa.Column("result", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("agent_id", UUID, nullable=True),
        sa.Column("swarm_id", UUID, nullable=True),
        sa.Column("workflow_id", UUID, nullable=True),
        sa.Column("parent_task_id", UUID, nullable=True),
        sa.Column("pollen_awarded", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("recipe_used_id", UUID, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_tasks_agent_id",
        ),
        sa.ForeignKeyConstraint(
            ["swarm_id"],
            ["sub_swarms.id"],
            name="fk_tasks_swarm_id",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            name="fk_tasks_workflow_id",
        ),
        sa.ForeignKeyConstraint(
            ["parent_task_id"],
            ["tasks.id"],
            name="fk_tasks_parent_task_id",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_used_id"],
            ["recipes.id"],
            name="fk_tasks_recipe_used_id",
        ),
    )
    op.create_index("ix_tasks_workflow_id", "tasks", ["workflow_id"], unique=False)
    op.create_index("ix_tasks_swarm_id", "tasks", ["swarm_id"], unique=False)

    op.create_table(
        "pollen_rewards",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("agent_id", UUID, nullable=False),
        sa.Column("task_id", UUID, nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("source_agent_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_pollen_rewards_agent_id",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_pollen_rewards_task_id",
        ),
        sa.ForeignKeyConstraint(
            ["source_agent_id"],
            ["agents.id"],
            name="fk_pollen_rewards_source_agent_id",
        ),
    )
    op.create_index("ix_pollen_rewards_agent_id", "pollen_rewards", ["agent_id"], unique=False)

    op.create_table(
        "imitation_events",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("copier_agent_id", UUID, nullable=False),
        sa.Column("copied_agent_id", UUID, nullable=False),
        sa.Column("recipe_id", UUID, nullable=True),
        sa.Column("outcome", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["copier_agent_id"],
            ["agents.id"],
            name="fk_imitation_copier_agent_id",
        ),
        sa.ForeignKeyConstraint(
            ["copied_agent_id"],
            ["agents.id"],
            name="fk_imitation_copied_agent_id",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name="fk_imitation_recipe_id",
        ),
    )

    op.create_table(
        "knowledge_items",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.String(length=160), nullable=True),
        sa.Column("neo4j_node_id", sa.String(length=160), nullable=True),
        sa.Column(
            "confidence_score",
            sa.Float(),
            server_default=sa.text("0.5"),
            nullable=False,
        ),
        sa.Column(
            "topic_tags",
            pg.JSONB(astext_type=sa.Text()),
            server_default=jsonb_arr,
            nullable=False,
        ),
        sa.Column(
            "decay_factor",
            sa.Float(),
            server_default=sa.text("1.0"),
            nullable=False,
        ),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_knowledge_items_topic_tags_gin",
        "knowledge_items",
        ["topic_tags"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_table(
        "learning_logs",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("agent_id", UUID, nullable=False),
        sa.Column("task_id", UUID, nullable=True),
        sa.Column("insight_text", sa.Text(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pollen_earned", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_learning_logs_agent_id",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_learning_logs_task_id",
        ),
    )

    op.create_table(
        "simulations",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("task_id", UUID, nullable=True),
        sa.Column("scenario", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_data", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_type", sa.String(length=32), nullable=False),
        sa.Column(
            "confidence_pct",
            sa.Float(),
            server_default=sa.text("0.0"),
            nullable=False,
        ),
        sa.Column("docker_container_id", sa.String(length=128), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_simulations_task_id",
        ),
    )

    op.create_table(
        "cost_records",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("agent_id", UUID, nullable=True),
        sa.Column("task_id", UUID, nullable=True),
        sa.Column("llm_model", sa.String(length=100), nullable=False),
        sa.Column("tokens_in", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_out", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_cost_records_agent_id",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_cost_records_task_id",
        ),
    )

    op.create_table(
        "budgets",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("limit_usd", sa.Float(), nullable=False),
        sa.Column(
            "spent_usd",
            sa.Float(),
            server_default=sa.text("0.0"),
            nullable=False,
        ),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop bee-hive tables in dependency-safe order."""

    op.drop_table("budgets")
    op.drop_table("cost_records")
    op.drop_table("simulations")
    op.drop_table("learning_logs")
    op.drop_index("ix_knowledge_items_topic_tags_gin", table_name="knowledge_items")
    op.drop_table("knowledge_items")
    op.drop_table("imitation_events")
    op.drop_index("ix_pollen_rewards_agent_id", table_name="pollen_rewards")
    op.drop_table("pollen_rewards")
    op.drop_index("ix_tasks_swarm_id", table_name="tasks")
    op.drop_index("ix_tasks_workflow_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_workflow_steps_workflow_id", table_name="workflow_steps")
    op.drop_table("workflow_steps")
    op.drop_table("workflows")
    op.drop_index("ix_recipes_topic_tags_gin", table_name="recipes")
    op.drop_table("recipes")
    op.drop_constraint("fk_sub_swarms_queen_agent_id", "sub_swarms", type_="foreignkey")
    op.drop_index("ix_agents_swarm_id", table_name="agents")
    op.drop_table("agents")
    op.drop_table("sub_swarms")
