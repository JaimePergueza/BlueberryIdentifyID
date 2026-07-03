"""Add human review layer for Petri segmentation regions

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "petri_region_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "petri_segmentation_region_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("petri_segmentation_regions.id"),
            nullable=False,
        ),
        sa.Column(
            "petri_segmentation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("petri_segmentation_runs.id"),
            nullable=False,
        ),
        sa.Column("dataset_release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_releases.id"), nullable=False),
        sa.Column("dataset_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_items.id"), nullable=False),
        sa.Column(
            "dataset_split_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_split_items.id"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reviewer_id", sa.String(length=255), nullable=True),
        sa.Column("reviewer_name", sa.String(length=255), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("corrected_bbox_x", sa.Integer(), nullable=True),
        sa.Column("corrected_bbox_y", sa.Integer(), nullable=True),
        sa.Column("corrected_bbox_width", sa.Integer(), nullable=True),
        sa.Column("corrected_bbox_height", sa.Integer(), nullable=True),
        sa.Column("corrected_notes", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "decision IN ('candidate_valid', 'candidate_false_positive', 'candidate_uncertain', "
            "'needs_resegmentation')",
            name="ck_petri_region_reviews_decision",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_petri_region_reviews_confidence_score",
        ),
        sa.CheckConstraint(
            "corrected_bbox_width IS NULL OR corrected_bbox_width > 0",
            name="ck_petri_region_reviews_corrected_bbox_width",
        ),
        sa.CheckConstraint(
            "corrected_bbox_height IS NULL OR corrected_bbox_height > 0",
            name="ck_petri_region_reviews_corrected_bbox_height",
        ),
    )
    op.create_index(
        "ix_petri_region_reviews_petri_segmentation_region_id",
        "petri_region_reviews",
        ["petri_segmentation_region_id"],
    )
    op.create_index(
        "ix_petri_region_reviews_petri_segmentation_run_id", "petri_region_reviews", ["petri_segmentation_run_id"]
    )
    op.create_index("ix_petri_region_reviews_dataset_release_id", "petri_region_reviews", ["dataset_release_id"])
    op.create_index("ix_petri_region_reviews_dataset_item_id", "petri_region_reviews", ["dataset_item_id"])
    op.create_index(
        "ix_petri_region_reviews_dataset_split_item_id", "petri_region_reviews", ["dataset_split_item_id"]
    )
    op.create_index("ix_petri_region_reviews_created_at", "petri_region_reviews", ["created_at"])
    op.create_index(
        "uq_petri_region_reviews_one_final_per_region",
        "petri_region_reviews",
        ["petri_segmentation_region_id"],
        unique=True,
        postgresql_where=sa.text("is_final = true"),
        sqlite_where=sa.text("is_final = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_petri_region_reviews_one_final_per_region", table_name="petri_region_reviews")
    op.drop_index("ix_petri_region_reviews_created_at", table_name="petri_region_reviews")
    op.drop_index("ix_petri_region_reviews_dataset_split_item_id", table_name="petri_region_reviews")
    op.drop_index("ix_petri_region_reviews_dataset_item_id", table_name="petri_region_reviews")
    op.drop_index("ix_petri_region_reviews_dataset_release_id", table_name="petri_region_reviews")
    op.drop_index("ix_petri_region_reviews_petri_segmentation_run_id", table_name="petri_region_reviews")
    op.drop_index("ix_petri_region_reviews_petri_segmentation_region_id", table_name="petri_region_reviews")
    op.drop_table("petri_region_reviews")
