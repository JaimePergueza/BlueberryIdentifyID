"""detection training artifact policies

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-05 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ARTIFACT_KINDS = (
    "planned_weights", "planned_metrics", "planned_predictions", "planned_logs",
    "planned_run_dir", "planned_config", "planned_manifest",
    "actual_weights", "actual_metrics", "actual_predictions", "actual_logs", "actual_manifest",
    "other",
)
_ARTIFACT_STATES = ("planned", "registered", "missing", "forbidden", "ignored", "deleted", "unknown")
_LOCATION_TYPES = ("local_path", "external_uri", "relative_path", "unresolved")


def upgrade() -> None:
    op.create_table(
        "detection_training_artifact_policies",
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
        sa.Column("is_policy_ready", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("artifact_root_dir", sa.Text(), nullable=True),
        sa.Column("planned_output_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("storage_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("git_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checksum_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("registry_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "decision IN ('artifact_policy_ready', 'needs_external_storage', 'blocked_by_repo_storage', "
            "'blocked_by_missing_output_dir', 'blocked_by_forbidden_extension', "
            "'blocked_by_policy_violation', 'blocked_by_environment')",
            name="ck_detection_training_artifact_policies_decision",
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'warning', 'blocked', 'failed')",
            name="ck_detection_training_artifact_policies_status",
        ),
    )
    op.create_index(
        "ix_dta_policies_detection_training_run_id",
        "detection_training_artifact_policies",
        ["detection_training_run_id"],
    )
    op.create_index(
        "ix_dta_policies_readiness_report_id", "detection_training_artifact_policies", ["readiness_report_id"]
    )
    op.create_index(
        "ix_dta_policies_environment_spec_id", "detection_training_artifact_policies", ["environment_spec_id"]
    )
    op.create_index(
        "ix_dta_policies_annotation_bundle_run_id",
        "detection_training_artifact_policies",
        ["annotation_bundle_run_id"],
    )
    op.create_index(
        "ix_dta_policies_dataset_release_id", "detection_training_artifact_policies", ["dataset_release_id"]
    )
    op.create_index("ix_dta_policies_created_at", "detection_training_artifact_policies", ["created_at"])

    op.create_table(
        "detection_training_artifact_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artifact_policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_artifact_policies.id"),
            nullable=False,
        ),
        sa.Column(
            "detection_training_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_runs.id"),
            nullable=False,
        ),
        sa.Column("artifact_kind", sa.String(length=32), nullable=False),
        sa.Column("artifact_state", sa.String(length=16), nullable=False),
        sa.Column("location_type", sa.String(length=16), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("relative_path", sa.Text(), nullable=True),
        sa.Column("external_uri", sa.Text(), nullable=True),
        sa.Column("file_extension", sa.String(length=32), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("artifact_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "artifact_kind IN (" + ", ".join(f"'{v}'" for v in _ARTIFACT_KINDS) + ")",
            name="ck_detection_training_artifact_records_kind",
        ),
        sa.CheckConstraint(
            "artifact_state IN (" + ", ".join(f"'{v}'" for v in _ARTIFACT_STATES) + ")",
            name="ck_detection_training_artifact_records_state",
        ),
        sa.CheckConstraint(
            "location_type IN (" + ", ".join(f"'{v}'" for v in _LOCATION_TYPES) + ")",
            name="ck_detection_training_artifact_records_location_type",
        ),
    )
    op.create_index(
        "ix_dta_records_artifact_policy_id", "detection_training_artifact_records", ["artifact_policy_id"]
    )
    op.create_index(
        "ix_dta_records_detection_training_run_id",
        "detection_training_artifact_records",
        ["detection_training_run_id"],
    )
    op.create_index("ix_dta_records_artifact_kind", "detection_training_artifact_records", ["artifact_kind"])
    op.create_index("ix_dta_records_artifact_state", "detection_training_artifact_records", ["artifact_state"])
    op.create_index("ix_dta_records_created_at", "detection_training_artifact_records", ["created_at"])

    op.create_table(
        "detection_training_artifact_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artifact_policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_training_artifact_policies.id"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('error', 'warning', 'info')", name="ck_detection_training_artifact_issues_severity"
        ),
    )
    op.create_index(
        "ix_dta_issues_artifact_policy_id", "detection_training_artifact_issues", ["artifact_policy_id"]
    )
    op.create_index("ix_dta_issues_severity", "detection_training_artifact_issues", ["severity"])
    op.create_index("ix_dta_issues_code", "detection_training_artifact_issues", ["code"])
    op.create_index("ix_dta_issues_created_at", "detection_training_artifact_issues", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_dta_issues_created_at", table_name="detection_training_artifact_issues")
    op.drop_index("ix_dta_issues_code", table_name="detection_training_artifact_issues")
    op.drop_index("ix_dta_issues_severity", table_name="detection_training_artifact_issues")
    op.drop_index("ix_dta_issues_artifact_policy_id", table_name="detection_training_artifact_issues")
    op.drop_table("detection_training_artifact_issues")

    op.drop_index("ix_dta_records_created_at", table_name="detection_training_artifact_records")
    op.drop_index("ix_dta_records_artifact_state", table_name="detection_training_artifact_records")
    op.drop_index("ix_dta_records_artifact_kind", table_name="detection_training_artifact_records")
    op.drop_index("ix_dta_records_detection_training_run_id", table_name="detection_training_artifact_records")
    op.drop_index("ix_dta_records_artifact_policy_id", table_name="detection_training_artifact_records")
    op.drop_table("detection_training_artifact_records")

    op.drop_index("ix_dta_policies_created_at", table_name="detection_training_artifact_policies")
    op.drop_index("ix_dta_policies_dataset_release_id", table_name="detection_training_artifact_policies")
    op.drop_index("ix_dta_policies_annotation_bundle_run_id", table_name="detection_training_artifact_policies")
    op.drop_index("ix_dta_policies_environment_spec_id", table_name="detection_training_artifact_policies")
    op.drop_index("ix_dta_policies_readiness_report_id", table_name="detection_training_artifact_policies")
    op.drop_index("ix_dta_policies_detection_training_run_id", table_name="detection_training_artifact_policies")
    op.drop_table("detection_training_artifact_policies")
