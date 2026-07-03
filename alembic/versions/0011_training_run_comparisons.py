"""Add training run comparison reports

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_run_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_release_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_releases.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("primary_metric", sa.String(length=32), nullable=False),
        sa.Column("primary_split", sa.String(length=32), nullable=False),
        sa.Column("selection_policy", sa.String(length=64), nullable=False),
        sa.Column(
            "selected_training_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("training_runs.id"),
            nullable=True,
        ),
        sa.Column("comparison_summary", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("primary_metric IN ('accuracy')", name="ck_training_run_comparisons_primary_metric"),
        sa.CheckConstraint(
            "primary_split IN ('validation', 'test')", name="ck_training_run_comparisons_primary_split"
        ),
        sa.CheckConstraint(
            "selection_policy IN ('best_primary_metric', 'prefer_simpler_if_tie', 'no_auto_selection')",
            name="ck_training_run_comparisons_selection_policy",
        ),
    )
    op.create_index(
        "ix_training_run_comparisons_dataset_release_id",
        "training_run_comparisons",
        ["dataset_release_id"],
    )
    op.create_index(
        "ix_training_run_comparisons_selected_training_run_id",
        "training_run_comparisons",
        ["selected_training_run_id"],
    )

    op.create_table(
        "training_run_comparison_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "comparison_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("training_run_comparisons.id"),
            nullable=False,
        ),
        sa.Column(
            "training_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("training_runs.id"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("run_kind", sa.String(length=32), nullable=False),
        sa.Column("baseline_model_type", sa.String(length=64), nullable=False),
        sa.Column("primary_metric_value", sa.Float(), nullable=True),
        sa.Column("train_accuracy", sa.Float(), nullable=True),
        sa.Column("validation_accuracy", sa.Float(), nullable=True),
        sa.Column("test_accuracy", sa.Float(), nullable=True),
        sa.Column("generalization_gap", sa.Float(), nullable=True),
        sa.Column("support_train", sa.Integer(), nullable=True),
        sa.Column("support_validation", sa.Integer(), nullable=True),
        sa.Column("support_test", sa.Integer(), nullable=True),
        sa.Column("metrics_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("comparison_id", "training_run_id", name="uq_training_run_comparison_entries_run"),
    )
    op.create_index(
        "ix_training_run_comparison_entries_comparison_id",
        "training_run_comparison_entries",
        ["comparison_id"],
    )
    op.create_index(
        "ix_training_run_comparison_entries_training_run_id",
        "training_run_comparison_entries",
        ["training_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_training_run_comparison_entries_training_run_id", table_name="training_run_comparison_entries")
    op.drop_index("ix_training_run_comparison_entries_comparison_id", table_name="training_run_comparison_entries")
    op.drop_table("training_run_comparison_entries")
    op.drop_index("ix_training_run_comparisons_selected_training_run_id", table_name="training_run_comparisons")
    op.drop_index("ix_training_run_comparisons_dataset_release_id", table_name="training_run_comparisons")
    op.drop_table("training_run_comparisons")
