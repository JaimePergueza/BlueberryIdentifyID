"""Add classical Petri segmentation reports

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "petri_segmentation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_releases.id"), nullable=False),
        sa.Column(
            "image_audit_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("image_dataset_audit_runs.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("processed_petri_images", sa.Integer(), nullable=False),
        sa.Column("failed_petri_images", sa.Integer(), nullable=False),
        sa.Column("total_regions_detected", sa.Integer(), nullable=False),
        sa.Column("mean_regions_per_image", sa.Float(), nullable=True),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('completed', 'partial', 'failed')", name="ck_petri_segmentation_runs_status"),
    )
    op.create_index("ix_petri_segmentation_runs_dataset_release_id", "petri_segmentation_runs", ["dataset_release_id"])
    op.create_index("ix_petri_segmentation_runs_image_audit_run_id", "petri_segmentation_runs", ["image_audit_run_id"])
    op.create_index("ix_petri_segmentation_runs_created_at", "petri_segmentation_runs", ["created_at"])

    op.create_table(
        "petri_segmentation_regions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "segmentation_run_id",
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
        sa.Column("split", sa.String(length=32), nullable=False),
        sa.Column("petri_image_path", sa.Text(), nullable=False),
        sa.Column("region_index", sa.Integer(), nullable=False),
        sa.Column("area_px", sa.Float(), nullable=False),
        sa.Column("perimeter_px", sa.Float(), nullable=True),
        sa.Column("centroid_x", sa.Float(), nullable=False),
        sa.Column("centroid_y", sa.Float(), nullable=False),
        sa.Column("bbox_x", sa.Integer(), nullable=False),
        sa.Column("bbox_y", sa.Integer(), nullable=False),
        sa.Column("bbox_width", sa.Integer(), nullable=False),
        sa.Column("bbox_height", sa.Integer(), nullable=False),
        sa.Column("circularity", sa.Float(), nullable=True),
        sa.Column("solidity", sa.Float(), nullable=True),
        sa.Column("mean_intensity", sa.Float(), nullable=True),
        sa.Column("region_features", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("split IN ('train', 'validation', 'test')", name="ck_petri_segmentation_regions_split"),
        sa.UniqueConstraint(
            "segmentation_run_id",
            "dataset_split_item_id",
            "region_index",
            name="uq_petri_segmentation_regions_run_split_item_index",
        ),
    )
    op.create_index("ix_petri_segmentation_regions_segmentation_run_id", "petri_segmentation_regions", ["segmentation_run_id"])
    op.create_index("ix_petri_segmentation_regions_dataset_release_id", "petri_segmentation_regions", ["dataset_release_id"])
    op.create_index("ix_petri_segmentation_regions_dataset_item_id", "petri_segmentation_regions", ["dataset_item_id"])
    op.create_index("ix_petri_segmentation_regions_dataset_split_item_id", "petri_segmentation_regions", ["dataset_split_item_id"])


def downgrade() -> None:
    op.drop_index("ix_petri_segmentation_regions_dataset_split_item_id", table_name="petri_segmentation_regions")
    op.drop_index("ix_petri_segmentation_regions_dataset_item_id", table_name="petri_segmentation_regions")
    op.drop_index("ix_petri_segmentation_regions_dataset_release_id", table_name="petri_segmentation_regions")
    op.drop_index("ix_petri_segmentation_regions_segmentation_run_id", table_name="petri_segmentation_regions")
    op.drop_table("petri_segmentation_regions")
    op.drop_index("ix_petri_segmentation_runs_created_at", table_name="petri_segmentation_runs")
    op.drop_index("ix_petri_segmentation_runs_image_audit_run_id", table_name="petri_segmentation_runs")
    op.drop_index("ix_petri_segmentation_runs_dataset_release_id", table_name="petri_segmentation_runs")
    op.drop_table("petri_segmentation_runs")
