"""Add baseline training runs and predictions

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_releases.id"), nullable=False),
        sa.Column("preflight_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("training_preflight_runs.id"), nullable=False),
        sa.Column("run_kind", sa.String(length=32), nullable=False),
        sa.Column("baseline_model_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("experiment_name", sa.String(length=255), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("baseline_state", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_training_runs_status"),
        sa.CheckConstraint("run_kind IN ('baseline')", name="ck_training_runs_run_kind"),
        sa.CheckConstraint("baseline_model_type IN ('majority_class')", name="ck_training_runs_baseline_model_type"),
    )
    op.create_index("ix_training_runs_dataset_release_id", "training_runs", ["dataset_release_id"])
    op.create_index("ix_training_runs_preflight_run_id", "training_runs", ["preflight_run_id"])

    op.create_table(
        "training_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("training_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("training_runs.id"), nullable=False),
        sa.Column("dataset_split_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_split_items.id"), nullable=False),
        sa.Column("dataset_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_items.id"), nullable=False),
        sa.Column("split", sa.String(length=32), nullable=False),
        sa.Column("ground_truth_label", sa.String(length=64), nullable=False),
        sa.Column("predicted_label", sa.String(length=64), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("split IN ('train', 'validation', 'test')", name="ck_training_predictions_split"),
        sa.CheckConstraint(
            "ground_truth_label IN ("
            "'no_evident_growth', 'suspicious_growth', 'probable_fungal_growth', "
            "'probable_bacterial_growth', 'inconclusive'"
            ")",
            name="ck_training_predictions_ground_truth_label",
        ),
        sa.CheckConstraint(
            "predicted_label IN ("
            "'no_evident_growth', 'suspicious_growth', 'probable_fungal_growth', "
            "'probable_bacterial_growth', 'inconclusive'"
            ")",
            name="ck_training_predictions_predicted_label",
        ),
        sa.UniqueConstraint("training_run_id", "dataset_split_item_id", name="uq_training_predictions_run_split_item"),
    )
    op.create_index("ix_training_predictions_training_run_id", "training_predictions", ["training_run_id"])
    op.create_index("ix_training_predictions_dataset_split_item_id", "training_predictions", ["dataset_split_item_id"])
    op.create_index("ix_training_predictions_dataset_item_id", "training_predictions", ["dataset_item_id"])


def downgrade() -> None:
    op.drop_index("ix_training_predictions_dataset_item_id", table_name="training_predictions")
    op.drop_index("ix_training_predictions_dataset_split_item_id", table_name="training_predictions")
    op.drop_index("ix_training_predictions_training_run_id", table_name="training_predictions")
    op.drop_table("training_predictions")
    op.drop_index("ix_training_runs_preflight_run_id", table_name="training_runs")
    op.drop_index("ix_training_runs_dataset_release_id", table_name="training_runs")
    op.drop_table("training_runs")
