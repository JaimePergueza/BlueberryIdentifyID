"""Add supervised Petri annotation exports

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "petri_annotation_export_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_releases.id"), nullable=False),
        sa.Column(
            "petri_segmentation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("petri_segmentation_runs.id"),
            nullable=False,
        ),
        sa.Column("export_format", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("exported_annotation_count", sa.Integer(), nullable=False),
        sa.Column("skipped_review_count", sa.Integer(), nullable=False),
        sa.Column("image_count", sa.Integer(), nullable=False),
        sa.Column("category_count", sa.Integer(), nullable=False),
        sa.Column("output_manifest", postgresql.JSONB(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "export_format IN ('blueberry_manifest', 'coco_json', 'yolo_txt')",
            name="ck_petri_annotation_export_runs_format",
        ),
        sa.CheckConstraint("status IN ('completed', 'partial', 'failed')", name="ck_petri_annotation_export_runs_status"),
    )
    op.create_index("ix_petri_annotation_export_runs_dataset_release_id", "petri_annotation_export_runs", ["dataset_release_id"])
    op.create_index(
        "ix_petri_annotation_export_runs_petri_segmentation_run_id",
        "petri_annotation_export_runs",
        ["petri_segmentation_run_id"],
    )
    op.create_index("ix_petri_annotation_export_runs_created_at", "petri_annotation_export_runs", ["created_at"])

    op.create_table(
        "petri_annotation_export_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "export_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("petri_annotation_export_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "petri_region_review_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("petri_region_reviews.id"),
            nullable=False,
        ),
        sa.Column(
            "petri_segmentation_region_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("petri_segmentation_regions.id"),
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
        sa.Column("split", sa.String(length=16), nullable=False),
        sa.Column("petri_image_path", sa.String(length=1024), nullable=False),
        sa.Column("export_label", sa.String(length=64), nullable=False),
        sa.Column("bbox_x", sa.Integer(), nullable=False),
        sa.Column("bbox_y", sa.Integer(), nullable=False),
        sa.Column("bbox_width", sa.Integer(), nullable=False),
        sa.Column("bbox_height", sa.Integer(), nullable=False),
        sa.Column("bbox_source", sa.String(length=16), nullable=False),
        sa.Column("export_payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("bbox_width > 0", name="ck_petri_annotation_export_items_bbox_width"),
        sa.CheckConstraint("bbox_height > 0", name="ck_petri_annotation_export_items_bbox_height"),
        sa.CheckConstraint("bbox_source IN ('corrected', 'original')", name="ck_petri_annotation_export_items_bbox_source"),
        sa.UniqueConstraint("export_run_id", "petri_region_review_id", name="uq_petri_annotation_export_items_run_review"),
    )
    op.create_index("ix_petri_annotation_export_items_export_run_id", "petri_annotation_export_items", ["export_run_id"])
    op.create_index(
        "ix_petri_annotation_export_items_petri_region_review_id",
        "petri_annotation_export_items",
        ["petri_region_review_id"],
    )
    op.create_index(
        "ix_petri_annotation_export_items_petri_segmentation_region_id",
        "petri_annotation_export_items",
        ["petri_segmentation_region_id"],
    )
    op.create_index(
        "ix_petri_annotation_export_items_dataset_release_id",
        "petri_annotation_export_items",
        ["dataset_release_id"],
    )
    op.create_index("ix_petri_annotation_export_items_dataset_item_id", "petri_annotation_export_items", ["dataset_item_id"])
    op.create_index(
        "ix_petri_annotation_export_items_dataset_split_item_id",
        "petri_annotation_export_items",
        ["dataset_split_item_id"],
    )
    op.create_index("ix_petri_annotation_export_items_split", "petri_annotation_export_items", ["split"])
    op.create_index("ix_petri_annotation_export_items_created_at", "petri_annotation_export_items", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_petri_annotation_export_items_created_at", table_name="petri_annotation_export_items")
    op.drop_index("ix_petri_annotation_export_items_split", table_name="petri_annotation_export_items")
    op.drop_index("ix_petri_annotation_export_items_dataset_split_item_id", table_name="petri_annotation_export_items")
    op.drop_index("ix_petri_annotation_export_items_dataset_item_id", table_name="petri_annotation_export_items")
    op.drop_index("ix_petri_annotation_export_items_dataset_release_id", table_name="petri_annotation_export_items")
    op.drop_index("ix_petri_annotation_export_items_petri_segmentation_region_id", table_name="petri_annotation_export_items")
    op.drop_index("ix_petri_annotation_export_items_petri_region_review_id", table_name="petri_annotation_export_items")
    op.drop_index("ix_petri_annotation_export_items_export_run_id", table_name="petri_annotation_export_items")
    op.drop_table("petri_annotation_export_items")
    op.drop_index("ix_petri_annotation_export_runs_created_at", table_name="petri_annotation_export_runs")
    op.drop_index("ix_petri_annotation_export_runs_petri_segmentation_run_id", table_name="petri_annotation_export_runs")
    op.drop_index("ix_petri_annotation_export_runs_dataset_release_id", table_name="petri_annotation_export_runs")
    op.drop_table("petri_annotation_export_runs")
