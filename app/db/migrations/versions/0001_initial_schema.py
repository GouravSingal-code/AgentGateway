"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.VARCHAR(255), nullable=False, unique=True),
        sa.Column("api_key", sa.VARCHAR(255), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("rate_limit_tokens_per_day", sa.Integer(), nullable=False, server_default="1000000"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("model", sa.VARCHAR(100), nullable=False),
        sa.Column("output", sa.Text()),
        sa.Column("tool_calls", postgresql.JSONB()),
        sa.Column("tokens_input", sa.Integer(), server_default="0"),
        sa.Column("tokens_output", sa.Integer(), server_default="0"),
        sa.Column("cost_usd", sa.Float(), server_default="0"),
        sa.Column("latency_ms", sa.Integer(), server_default="0"),
        sa.Column("status", sa.VARCHAR(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("tool_name", sa.VARCHAR(100), nullable=False),
        sa.Column("input_args", postgresql.JSONB()),
        sa.Column("output", postgresql.JSONB()),
        sa.Column("status", sa.VARCHAR(20), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_run_id", "audit_logs", ["run_id"])

    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("suite_name", sa.VARCHAR(100), nullable=False),
        sa.Column("test_case_id", sa.VARCHAR(100), nullable=False),
        sa.Column("model", sa.VARCHAR(100), nullable=False),
        sa.Column("accuracy_score", sa.Float(), server_default="0"),
        sa.Column("routed_from", sa.VARCHAR(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("eval_results")
    op.drop_index("ix_audit_logs_run_id", "audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", "audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("agent_runs")
    op.drop_table("tenants")
