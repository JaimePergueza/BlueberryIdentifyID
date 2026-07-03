"""annotation quality gates

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-03 19:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "annotation_quality_gate_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("annotation_bundle_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("annotation_bundle_runs.id"), nullable=False),
        sa.Column("dataset_release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_releases.id"), nullable=False),
        sa.Column("petri_annotation_export_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("petri_annotation_export_runs.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_passed", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total_images", sa.Integer(), nullable=False),
        sa.Column("total_annotations", sa.Integer(), nullable=False),
        sa.Column("train_image_count", sa.Integer(), nullable=False),
        sa.Column("validation_image_count", sa.Integer(), nullable=False),
        sa.Column("test_image_count", sa.Integer(), nullable=False),
        sa.Column("train_annotation_count", sa.Integer(), nullable=False),
        sa.Column("validation_annotation_count", sa.Integer(), nullable=False),
        sa.Column("test_annotation_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("quality_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("split_distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bbox_statistics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("category_distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('passed', 'warning', 'failed')", name="ck_annotation_quality_gate_runs_status"),
    )
    op.create_index("ix_annotation_quality_gate_runs_annotation_bundle_run_id", "annotation_quality_gate_runs", ["annotation_bundle_run_id"])
    op.create_index("ix_annotation_quality_gate_runs_dataset_release_id", "annotation_quality_gate_runs", ["dataset_release_id"])
    op.create_index("ix_annotation_quality_gate_runs_petri_annotation_export_run_id", "annotation_quality_gate_runs", ["petri_annotation_export_run_id"])
    op.create_index("ix_annotation_quality_gate_runs_created_at", "annotation_quality_gate_runs", ["created_at"])

    op.create_table(
        "annotation_quality_gate_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quality_gate_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("annotation_quality_gate_runs.id"), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("split", sa.String(length=32), nullable=True),
        sa.Column("image_path", sa.String(length=2048), nullable=True),
        sa.Column("annotation_ref", sa.String(length=255), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('error', 'warning')", name="ck_annotation_quality_gate_issues_severity"),
        sa.CheckConstraint("split IS NULL OR split IN ('train', 'validation', 'test')", name="ck_annotation_quality_gate_issues_split"),
    )
    op.create_index("ix_annotation_quality_gate_issues_quality_gate_run_id", "annotation_quality_gate_issues", ["quality_gate_run_id"])
    op.create_index("ix_annotation_quality_gate_issues_severity", "annotation_quality_gate_issues", ["severity"])
    op.create_index("ix_annotation_quality_gate_issues_code", "annotation_quality_gate_issues", ["code"])
    op.create_index("ix_annotation_quality_gate_issues_split", "annotation_quality_gate_issues", ["split"])
    op.create_index("ix_annotation_quality_gate_issues_created_at", "annotation_quality_gate_issues", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_annotation_quality_gate_issues_created_at", table_name="annotation_quality_gate_issues")
    op.drop_index("ix_annotation_quality_gate_issues_split", table_name="annotation_quality_gate_issues")
    op.drop_index("ix_annotation_quality_gate_issues_code", table_name="annotation_quality_gate_issues")
    op.drop_index("ix_annotation_quality_gate_issues_severity", table_name="annotation_quality_gate_issues")
    op.drop_index("ix_annotation_quality_gate_issues_quality_gate_run_id", table_name="annotation_quality_gate_issues")
    op.drop_table("annotation_quality_gate_issues")
    op.drop_index("ix_annotation_quality_gate_runs_created_at", table_name="annotation_quality_gate_runs")
    op.drop_index("ix_annotation_quality_gate_runs_petri_annotation_export_run_id", table_name="annotation_quality_gate_runs")
    op.drop_index("ix_annotation_quality_gate_runs_dataset_release_id", table_name="annotation_quality_gate_runs")
    op.drop_index("ix_annotation_quality_gate_runs_annotation_bundle_run_id", table_name="annotation_quality_gate_runs")
    op.drop_table("annotation_quality_gate_runs")
