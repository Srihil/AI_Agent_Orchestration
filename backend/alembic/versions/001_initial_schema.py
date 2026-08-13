"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False, unique=True),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("current_agent", sa.String(100)),
        sa.Column("step_count", sa.Integer(), default=0),
        sa.Column("max_steps", sa.Integer(), default=20),
        sa.Column("require_approval", sa.Boolean(), default=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("final_response", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("metadata", JSONB),
    )
    op.create_index("ix_workflow_runs_user_id", "workflow_runs", ["user_id"])
    op.create_index("ix_workflow_runs_thread_id", "workflow_runs", ["thread_id"])
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"])

    op.create_table(
        "workflow_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workflow_run_id", sa.String(), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("agent_name", sa.String(100)),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("tool_name", sa.String(100)),
        sa.Column("status", sa.String(50), nullable=False, default="info"),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("result_summary", sa.Text()),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_workflow_events_workflow_run_id", "workflow_events", ["workflow_run_id"])
    op.create_index("ix_workflow_events_timestamp", "workflow_events", ["timestamp"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workflow_run_id", sa.String(), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("requesting_agent", sa.String(100), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(50), nullable=False, default="medium"),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_note", sa.Text()),
    )
    op.create_index("ix_approvals_workflow_run_id", "approvals", ["workflow_run_id"])
    op.create_index("ix_approvals_thread_id", "approvals", ["thread_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])

    op.create_table(
        "memories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False, default="fact"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memories_user_id", "memories", ["user_id"])
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"])

    op.create_table(
        "agent_executions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workflow_run_id", sa.String(), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50), nullable=False, default="running"),
        sa.Column("tool_calls_count", sa.Integer(), default=0),
        sa.Column("retry_count", sa.Integer(), default=0),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_agent_executions_workflow_run_id", "agent_executions", ["workflow_run_id"])
    op.create_index("ix_agent_executions_agent_name", "agent_executions", ["agent_name"])

    op.create_table(
        "tool_executions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workflow_run_id", sa.String(), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_execution_id", sa.String(), sa.ForeignKey("agent_executions.id", ondelete="SET NULL")),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input_summary", sa.Text()),
        sa.Column("output_summary", sa.Text()),
        sa.Column("status", sa.String(50), nullable=False, default="running"),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("retry_count", sa.Integer(), default=0),
        sa.Column("error", sa.Text()),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tool_executions_workflow_run_id", "tool_executions", ["workflow_run_id"])
    op.create_index("ix_tool_executions_tool_name", "tool_executions", ["tool_name"])


def downgrade() -> None:
    op.drop_table("tool_executions")
    op.drop_table("agent_executions")
    op.drop_table("memories")
    op.drop_table("approvals")
    op.drop_table("workflow_events")
    op.drop_table("workflow_runs")
    op.drop_table("users")
