"""Add supervised annotation export bundles

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "annotation_bundle_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("petri_annotation_export_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("petri_annotation_export_runs.id"), nullable=False),
        sa.Column("dataset_release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_releases.id"), nullable=False),
        sa.Column("petri_segmentation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("petri_segmentation_runs.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("output_dir", sa.String(length=1024), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("annotation_count", sa.Integer(), nullable=False),
        sa.Column("image_count", sa.Integer(), nullable=False),
        sa.Column("label_count", sa.Integer(), nullable=False),
        sa.Column("validation_summary", postgresql.JSONB(), nullable=False),
        sa.Column("bundle_manifest", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('completed', 'failed', 'dry_run')", name="ck_annotation_bundle_runs_status"),
    )
    op.create_index("ix_annotation_bundle_runs_petri_annotation_export_run_id", "annotation_bundle_runs", ["petri_annotation_export_run_id"])
    op.create_index("ix_annotation_bundle_runs_dataset_release_id", "annotation_bundle_runs", ["dataset_release_id"])
    op.create_index("ix_annotation_bundle_runs_petri_segmentation_run_id", "annotation_bundle_runs", ["petri_segmentation_run_id"])
    op.create_index("ix_annotation_bundle_runs_created_at", "annotation_bundle_runs", ["created_at"])

    op.create_table(
        "annotation_bundle_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bundle_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("annotation_bundle_runs.id"), nullable=False),
        sa.Column("file_role", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.String(length=2048), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "file_role IN ('coco_annotations', 'yolo_label', 'blueberry_manifest', 'dataset_yaml', "
            "'readme', 'bundle_manifest', 'copied_image')",
            name="ck_annotation_bundle_files_role",
        ),
    )
    op.create_index("ix_annotation_bundle_files_bundle_run_id", "annotation_bundle_files", ["bundle_run_id"])
    op.create_index("ix_annotation_bundle_files_file_role", "annotation_bundle_files", ["file_role"])
    op.create_index("ix_annotation_bundle_files_created_at", "annotation_bundle_files", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_annotation_bundle_files_created_at", table_name="annotation_bundle_files")
    op.drop_index("ix_annotation_bundle_files_file_role", table_name="annotation_bundle_files")
    op.drop_index("ix_annotation_bundle_files_bundle_run_id", table_name="annotation_bundle_files")
    op.drop_table("annotation_bundle_files")
    op.drop_index("ix_annotation_bundle_runs_created_at", table_name="annotation_bundle_runs")
    op.drop_index("ix_annotation_bundle_runs_petri_segmentation_run_id", table_name="annotation_bundle_runs")
    op.drop_index("ix_annotation_bundle_runs_dataset_release_id", table_name="annotation_bundle_runs")
    op.drop_index("ix_annotation_bundle_runs_petri_annotation_export_run_id", table_name="annotation_bundle_runs")
    op.drop_table("annotation_bundle_runs")
