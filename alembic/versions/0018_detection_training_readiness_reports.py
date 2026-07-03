"""detection training readiness reports

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-04 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "detection_training_readiness_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "detection_training_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_runs.id"),
            nullable=False,
        ),
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
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_ready", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("split_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("environment_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("contract_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendation_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("info_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "decision IN ('ready_for_training', 'needs_more_annotations', 'blocked_by_quality', "
            "'blocked_by_environment', 'blocked_by_contract', 'blocked_by_configuration')",
            name="ck_detection_training_readiness_reports_decision",
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'warning', 'blocked', 'failed')",
            name="ck_detection_training_readiness_reports_status",
        ),
    )
    op.create_index(
        "ix_detection_training_readiness_reports_detection_training_run_id",
        "detection_training_readiness_reports",
        ["detection_training_run_id"],
    )
    op.create_index(
        "ix_detection_training_readiness_reports_annotation_bundle_run_id",
        "detection_training_readiness_reports",
        ["annotation_bundle_run_id"],
    )
    op.create_index(
        "ix_detection_training_readiness_reports_annotation_quality_gate_run_id",
        "detection_training_readiness_reports",
        ["annotation_quality_gate_run_id"],
    )
    op.create_index(
        "ix_detection_training_readiness_reports_dataset_release_id",
        "detection_training_readiness_reports",
        ["dataset_release_id"],
    )
    op.create_index(
        "ix_detection_training_readiness_reports_petri_annotation_export_run_id",
        "detection_training_readiness_reports",
        ["petri_annotation_export_run_id"],
    )
    op.create_index(
        "ix_detection_training_readiness_reports_created_at",
        "detection_training_readiness_reports",
        ["created_at"],
    )

    op.create_table(
        "detection_training_readiness_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "readiness_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_readiness_reports.id"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('error', 'warning', 'info')", name="ck_detection_training_readiness_issues_severity"
        ),
    )
    op.create_index(
        "ix_detection_training_readiness_issues_readiness_report_id",
        "detection_training_readiness_issues",
        ["readiness_report_id"],
    )
    op.create_index("ix_detection_training_readiness_issues_severity", "detection_training_readiness_issues", ["severity"])
    op.create_index("ix_detection_training_readiness_issues_code", "detection_training_readiness_issues", ["code"])
    op.create_index(
        "ix_detection_training_readiness_issues_created_at", "detection_training_readiness_issues", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_detection_training_readiness_issues_created_at", table_name="detection_training_readiness_issues")
    op.drop_index("ix_detection_training_readiness_issues_code", table_name="detection_training_readiness_issues")
    op.drop_index("ix_detection_training_readiness_issues_severity", table_name="detection_training_readiness_issues")
    op.drop_index(
        "ix_detection_training_readiness_issues_readiness_report_id", table_name="detection_training_readiness_issues"
    )
    op.drop_table("detection_training_readiness_issues")
    op.drop_index(
        "ix_detection_training_readiness_reports_created_at", table_name="detection_training_readiness_reports"
    )
    op.drop_index(
        "ix_detection_training_readiness_reports_petri_annotation_export_run_id",
        table_name="detection_training_readiness_reports",
    )
    op.drop_index(
        "ix_detection_training_readiness_reports_dataset_release_id",
        table_name="detection_training_readiness_reports",
    )
    op.drop_index(
        "ix_detection_training_readiness_reports_annotation_quality_gate_run_id",
        table_name="detection_training_readiness_reports",
    )
    op.drop_index(
        "ix_detection_training_readiness_reports_annotation_bundle_run_id",
        table_name="detection_training_readiness_reports",
    )
    op.drop_index(
        "ix_detection_training_readiness_reports_detection_training_run_id",
        table_name="detection_training_readiness_reports",
    )
    op.drop_table("detection_training_readiness_reports")
