"""detection training execution runs

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-06 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUSES = ("blocked", "manual_required", "ready_to_execute", "failed")
_DECISIONS = (
    "blocked_by_prerequisites",
    "blocked_by_ci",
    "blocked_by_repository_safety",
    "blocked_by_artifact_policy",
    "blocked_by_environment",
    "blocked_by_readiness",
    "blocked_by_configuration",
    "manual_confirmation_required",
    "ready_for_manual_execution",
)
_MODES = ("scaffold_only", "manual_gate")


def upgrade() -> None:
    op.create_table(
        "detection_training_execution_runs",
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
            "environment_spec_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_environment_specs.id"),
            nullable=False,
        ),
        sa.Column(
            "artifact_policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_artifact_policies.id"),
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
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("is_executable", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prerequisite_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("repository_safety_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("execution_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("command_preview", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "status IN (" + ", ".join(f"'{v}'" for v in _STATUSES) + ")", name="ck_dtex_runs_status"
        ),
        sa.CheckConstraint(
            "decision IN (" + ", ".join(f"'{v}'" for v in _DECISIONS) + ")", name="ck_dtex_runs_decision"
        ),
        sa.CheckConstraint("mode IN (" + ", ".join(f"'{v}'" for v in _MODES) + ")", name="ck_dtex_runs_mode"),
    )
    op.create_index(
        "ix_dtex_runs_detection_training_run_id", "detection_training_execution_runs", ["detection_training_run_id"]
    )
    op.create_index(
        "ix_dtex_runs_readiness_report_id", "detection_training_execution_runs", ["readiness_report_id"]
    )
    op.create_index(
        "ix_dtex_runs_environment_spec_id", "detection_training_execution_runs", ["environment_spec_id"]
    )
    op.create_index("ix_dtex_runs_artifact_policy_id", "detection_training_execution_runs", ["artifact_policy_id"])
    op.create_index(
        "ix_dtex_runs_annotation_bundle_run_id", "detection_training_execution_runs", ["annotation_bundle_run_id"]
    )
    op.create_index("ix_dtex_runs_dataset_release_id", "detection_training_execution_runs", ["dataset_release_id"])
    op.create_index("ix_dtex_runs_created_at", "detection_training_execution_runs", ["created_at"])

    op.create_table(
        "detection_training_execution_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "execution_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_execution_runs.id"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('error', 'warning', 'info')", name="ck_dtex_issues_severity"),
    )
    op.create_index("ix_dtex_issues_execution_run_id", "detection_training_execution_issues", ["execution_run_id"])
    op.create_index("ix_dtex_issues_severity", "detection_training_execution_issues", ["severity"])
    op.create_index("ix_dtex_issues_code", "detection_training_execution_issues", ["code"])
    op.create_index("ix_dtex_issues_created_at", "detection_training_execution_issues", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_dtex_issues_created_at", table_name="detection_training_execution_issues")
    op.drop_index("ix_dtex_issues_code", table_name="detection_training_execution_issues")
    op.drop_index("ix_dtex_issues_severity", table_name="detection_training_execution_issues")
    op.drop_index("ix_dtex_issues_execution_run_id", table_name="detection_training_execution_issues")
    op.drop_table("detection_training_execution_issues")

    op.drop_index("ix_dtex_runs_created_at", table_name="detection_training_execution_runs")
    op.drop_index("ix_dtex_runs_dataset_release_id", table_name="detection_training_execution_runs")
    op.drop_index("ix_dtex_runs_annotation_bundle_run_id", table_name="detection_training_execution_runs")
    op.drop_index("ix_dtex_runs_artifact_policy_id", table_name="detection_training_execution_runs")
    op.drop_index("ix_dtex_runs_environment_spec_id", table_name="detection_training_execution_runs")
    op.drop_index("ix_dtex_runs_readiness_report_id", table_name="detection_training_execution_runs")
    op.drop_index("ix_dtex_runs_detection_training_run_id", table_name="detection_training_execution_runs")
    op.drop_table("detection_training_execution_runs")
