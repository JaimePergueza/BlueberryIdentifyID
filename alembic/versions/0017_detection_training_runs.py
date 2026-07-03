"""detection training runs (dry-run only)

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-04 09:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "detection_training_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "annotation_bundle_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("annotation_bundle_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "annotation_quality_gate_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("annotation_quality_gate_runs.id"),
            nullable=True,
        ),
        sa.Column("dataset_release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_releases.id"), nullable=False),
        sa.Column(
            "petri_annotation_export_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("petri_annotation_export_runs.id"),
            nullable=False,
        ),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_runnable", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("training_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("command_preview", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dataset_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_gate_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("issue_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint("algorithm IN ('yolo_dry_run')", name="ck_detection_training_runs_algorithm"),
        sa.CheckConstraint("mode IN ('dry_run')", name="ck_detection_training_runs_mode"),
        sa.CheckConstraint("status IN ('planned', 'blocked', 'failed')", name="ck_detection_training_runs_status"),
    )
    op.create_index(
        "ix_detection_training_runs_annotation_bundle_run_id",
        "detection_training_runs",
        ["annotation_bundle_run_id"],
    )
    op.create_index(
        "ix_detection_training_runs_annotation_quality_gate_run_id",
        "detection_training_runs",
        ["annotation_quality_gate_run_id"],
    )
    op.create_index("ix_detection_training_runs_dataset_release_id", "detection_training_runs", ["dataset_release_id"])
    op.create_index(
        "ix_detection_training_runs_petri_annotation_export_run_id",
        "detection_training_runs",
        ["petri_annotation_export_run_id"],
    )
    op.create_index("ix_detection_training_runs_created_at", "detection_training_runs", ["created_at"])

    op.create_table(
        "detection_training_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "detection_training_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_runs.id"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('error', 'warning', 'info')", name="ck_detection_training_issues_severity"),
    )
    op.create_index(
        "ix_detection_training_issues_detection_training_run_id",
        "detection_training_issues",
        ["detection_training_run_id"],
    )
    op.create_index("ix_detection_training_issues_severity", "detection_training_issues", ["severity"])
    op.create_index("ix_detection_training_issues_code", "detection_training_issues", ["code"])
    op.create_index("ix_detection_training_issues_created_at", "detection_training_issues", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_detection_training_issues_created_at", table_name="detection_training_issues")
    op.drop_index("ix_detection_training_issues_code", table_name="detection_training_issues")
    op.drop_index("ix_detection_training_issues_severity", table_name="detection_training_issues")
    op.drop_index("ix_detection_training_issues_detection_training_run_id", table_name="detection_training_issues")
    op.drop_table("detection_training_issues")
    op.drop_index("ix_detection_training_runs_created_at", table_name="detection_training_runs")
    op.drop_index("ix_detection_training_runs_petri_annotation_export_run_id", table_name="detection_training_runs")
    op.drop_index("ix_detection_training_runs_dataset_release_id", table_name="detection_training_runs")
    op.drop_index("ix_detection_training_runs_annotation_quality_gate_run_id", table_name="detection_training_runs")
    op.drop_index("ix_detection_training_runs_annotation_bundle_run_id", table_name="detection_training_runs")
    op.drop_table("detection_training_runs")
