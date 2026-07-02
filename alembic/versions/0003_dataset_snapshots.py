"""Add curated dataset snapshots and items

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

predicted_label_enum = postgresql.ENUM(
    "no_evident_growth",
    "suspicious_growth",
    "probable_fungal_growth",
    "probable_bacterial_growth",
    "inconclusive",
    name="predicted_label",
    create_type=False,
)
review_decision_enum = postgresql.ENUM(
    "confirmed",
    "corrected",
    "marked_inconclusive",
    "rejected_invalid_sample",
    name="review_decision",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "dataset_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("selection_criteria", postgresql.JSONB(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label_distribution", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("name", "version", name="uq_dataset_snapshots_name_version"),
    )

    op.create_table(
        "dataset_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_snapshots.id"),
            nullable=False,
        ),
        sa.Column(
            "analysis_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id"),
            nullable=False,
        ),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("samples.id"), nullable=False),
        sa.Column("petri_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("petri_images.id"), nullable=False),
        sa.Column("micro_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("micro_images.id"), nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("predictions.id"), nullable=False),
        sa.Column("final_review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("human_reviews.id"), nullable=False),
        sa.Column("ground_truth_label", predicted_label_enum, nullable=True),
        sa.Column("source_review_decision", review_decision_enum, nullable=False),
        sa.Column("included", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("exclusion_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "dataset_snapshot_id",
            "analysis_run_id",
            name="uq_dataset_items_snapshot_analysis_run",
        ),
    )
    op.create_index("ix_dataset_items_dataset_snapshot_id", "dataset_items", ["dataset_snapshot_id"])
    op.create_index("ix_dataset_items_analysis_run_id", "dataset_items", ["analysis_run_id"])


def downgrade() -> None:
    op.drop_index("ix_dataset_items_analysis_run_id", table_name="dataset_items")
    op.drop_index("ix_dataset_items_dataset_snapshot_id", table_name="dataset_items")
    op.drop_table("dataset_items")
    op.drop_table("dataset_snapshots")

