"""detection training environment specs

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-04 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "detection_training_environment_specs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "detection_training_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "readiness_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_readiness_reports.id"),
            nullable=False,
        ),
        sa.Column(
            "annotation_bundle_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("annotation_bundle_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "dataset_release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_releases.id"), nullable=False
        ),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_environment_ready", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("detected_environment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dependency_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hardware_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("artifact_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("execution_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("setup_instructions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("safe_check_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "decision IN ('environment_ready', 'needs_manual_setup', 'blocked_by_missing_requirements', "
            "'blocked_by_policy', 'blocked_by_unsupported_platform', 'blocked_by_storage_policy', "
            "'blocked_by_dependency_policy')",
            name="ck_detection_training_environment_specs_decision",
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'warning', 'blocked', 'failed')",
            name="ck_detection_training_environment_specs_status",
        ),
    )
    op.create_index(
        "ix_dte_specs_detection_training_run_id",
        "detection_training_environment_specs",
        ["detection_training_run_id"],
    )
    op.create_index(
        "ix_dte_specs_readiness_report_id",
        "detection_training_environment_specs",
        ["readiness_report_id"],
    )
    op.create_index(
        "ix_dte_specs_annotation_bundle_run_id",
        "detection_training_environment_specs",
        ["annotation_bundle_run_id"],
    )
    op.create_index(
        "ix_dte_specs_dataset_release_id",
        "detection_training_environment_specs",
        ["dataset_release_id"],
    )
    op.create_index(
        "ix_dte_specs_created_at",
        "detection_training_environment_specs",
        ["created_at"],
    )

    op.create_table(
        "detection_training_environment_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "environment_spec_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_environment_specs.id"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('error', 'warning', 'info')", name="ck_detection_training_environment_issues_severity"
        ),
    )
    op.create_index(
        "ix_dte_issues_environment_spec_id",
        "detection_training_environment_issues",
        ["environment_spec_id"],
    )
    op.create_index("ix_dte_issues_severity", "detection_training_environment_issues", ["severity"])
    op.create_index("ix_dte_issues_code", "detection_training_environment_issues", ["code"])
    op.create_index("ix_dte_issues_created_at", "detection_training_environment_issues", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_dte_issues_created_at", table_name="detection_training_environment_issues")
    op.drop_index("ix_dte_issues_code", table_name="detection_training_environment_issues")
    op.drop_index("ix_dte_issues_severity", table_name="detection_training_environment_issues")
    op.drop_index("ix_dte_issues_environment_spec_id", table_name="detection_training_environment_issues")
    op.drop_table("detection_training_environment_issues")
    op.drop_index("ix_dte_specs_created_at", table_name="detection_training_environment_specs")
    op.drop_index("ix_dte_specs_dataset_release_id", table_name="detection_training_environment_specs")
    op.drop_index("ix_dte_specs_annotation_bundle_run_id", table_name="detection_training_environment_specs")
    op.drop_index("ix_dte_specs_readiness_report_id", table_name="detection_training_environment_specs")
    op.drop_index("ix_dte_specs_detection_training_run_id", table_name="detection_training_environment_specs")
    op.drop_table("detection_training_environment_specs")
