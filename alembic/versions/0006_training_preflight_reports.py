"""Add persistent ML preflight validation reports

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_preflight_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_release_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_releases.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("train_count", sa.Integer(), nullable=False),
        sa.Column("validation_count", sa.Integer(), nullable=False),
        sa.Column("test_count", sa.Integer(), nullable=False),
        sa.Column("label_counts", postgresql.JSONB(), nullable=False),
        sa.Column("split_counts", postgresql.JSONB(), nullable=False),
        sa.Column("split_label_counts", postgresql.JSONB(), nullable=False),
        sa.Column("leakage_checks", postgresql.JSONB(), nullable=False),
        sa.Column("recommendation_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('passed', 'failed', 'warning')", name="ck_training_preflight_runs_status"),
    )
    op.create_index(
        "ix_training_preflight_runs_dataset_release_id",
        "training_preflight_runs",
        ["dataset_release_id"],
    )
    op.create_index("ix_training_preflight_runs_created_at", "training_preflight_runs", ["created_at"])

    op.create_table(
        "training_preflight_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "preflight_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("training_preflight_runs.id"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("field", sa.String(length=255), nullable=True),
        sa.Column("item_ref", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('error', 'warning')", name="ck_training_preflight_issues_severity"),
    )
    op.create_index(
        "ix_training_preflight_issues_preflight_run_id",
        "training_preflight_issues",
        ["preflight_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_training_preflight_issues_preflight_run_id", table_name="training_preflight_issues")
    op.drop_table("training_preflight_issues")
    op.drop_index("ix_training_preflight_runs_created_at", table_name="training_preflight_runs")
    op.drop_index("ix_training_preflight_runs_dataset_release_id", table_name="training_preflight_runs")
    op.drop_table("training_preflight_runs")
