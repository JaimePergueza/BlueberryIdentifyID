"""Add dataset curation runs and items

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


dataset_curation_run_status = postgresql.ENUM(
    "completed",
    "failed",
    name="dataset_curation_run_status",
    create_type=False,
)
dataset_curation_status = postgresql.ENUM(
    "included",
    "excluded_pending_review",
    "excluded_invalid_sample",
    "excluded_missing_prediction",
    "excluded_missing_images",
    "excluded_invalid_label",
    "excluded_duplicate",
    "excluded_policy",
    name="dataset_curation_status",
    create_type=False,
)
predicted_label = postgresql.ENUM(
    "no_evident_growth",
    "suspicious_growth",
    "probable_fungal_growth",
    "probable_bacterial_growth",
    "inconclusive",
    name="predicted_label",
    create_type=False,
)
review_decision = postgresql.ENUM(
    "confirmed",
    "corrected",
    "marked_inconclusive",
    "rejected_invalid_sample",
    name="review_decision",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    dataset_curation_run_status.create(bind, checkfirst=True)
    dataset_curation_status.create(bind, checkfirst=True)

    op.create_table(
        "dataset_curation_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("status", dataset_curation_run_status, server_default="completed", nullable=False),
        sa.Column("policy", PortableJSON(), nullable=True),
        sa.Column("total_candidates_scanned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("included_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("excluded_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_snapshot_id", sa.UUID(), nullable=True),
        sa.Column("issues", PortableJSON(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_snapshot_id"], ["dataset_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dataset_curation_runs_created_snapshot_id",
        "dataset_curation_runs",
        ["created_snapshot_id"],
    )

    op.create_table(
        "dataset_curation_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("curation_run_id", sa.UUID(), nullable=False),
        sa.Column("sample_id", sa.UUID(), nullable=True),
        sa.Column("analysis_run_id", sa.UUID(), nullable=True),
        sa.Column("prediction_id", sa.UUID(), nullable=True),
        sa.Column("human_review_id", sa.UUID(), nullable=True),
        sa.Column("petri_image_id", sa.UUID(), nullable=True),
        sa.Column("micro_image_id", sa.UUID(), nullable=True),
        sa.Column("automatic_label", predicted_label, nullable=True),
        sa.Column("final_label", predicted_label, nullable=True),
        sa.Column("review_decision", review_decision, nullable=True),
        sa.Column("curation_status", dataset_curation_status, nullable=False),
        sa.Column("exclusion_reason", sa.String(length=255), nullable=True),
        sa.Column("provenance", PortableJSON(), nullable=True),
        sa.Column("feature_summary", PortableJSON(), nullable=True),
        sa.Column("quality_summary", PortableJSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.ForeignKeyConstraint(["curation_run_id"], ["dataset_curation_runs.id"]),
        sa.ForeignKeyConstraint(["human_review_id"], ["human_reviews.id"]),
        sa.ForeignKeyConstraint(["micro_image_id"], ["micro_images.id"]),
        sa.ForeignKeyConstraint(["petri_image_id"], ["petri_images.id"]),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "curation_run_id",
            "analysis_run_id",
            name="uq_dataset_curation_items_run_analysis_run",
        ),
    )
    op.create_index("ix_dataset_curation_items_analysis_run_id", "dataset_curation_items", ["analysis_run_id"])
    op.create_index("ix_dataset_curation_items_curation_run_id", "dataset_curation_items", ["curation_run_id"])


def downgrade() -> None:
    op.drop_index("ix_dataset_curation_items_curation_run_id", table_name="dataset_curation_items")
    op.drop_index("ix_dataset_curation_items_analysis_run_id", table_name="dataset_curation_items")
    op.drop_table("dataset_curation_items")
    op.drop_index("ix_dataset_curation_runs_created_snapshot_id", table_name="dataset_curation_runs")
    op.drop_table("dataset_curation_runs")

    bind = op.get_bind()
    dataset_curation_status.drop(bind, checkfirst=True)
    dataset_curation_run_status.drop(bind, checkfirst=True)
