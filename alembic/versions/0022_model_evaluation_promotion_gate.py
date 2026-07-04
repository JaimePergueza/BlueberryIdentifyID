"""model evaluation and promotion gate

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa

from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("local_yolo_training_execution_run_id", sa.UUID(), nullable=True),
        sa.Column("detection_training_run_id", sa.UUID(), nullable=True),
        sa.Column("model_version_id", sa.UUID(), nullable=True),
        sa.Column("candidate_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("model_artifact_path", sa.Text(), nullable=False),
        sa.Column("model_artifact_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("model_artifact_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("metrics_artifact_path", sa.Text(), nullable=True),
        sa.Column("config_artifact_path", sa.Text(), nullable=True),
        sa.Column("source_summary", PortableJSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("candidate_kind IN ('smoke_yolo', 'experimental_yolo', 'classical_baseline', 'other')", name="ck_mc_kind"),
        sa.CheckConstraint("status IN ('created', 'evaluated', 'blocked', 'promoted', 'archived', 'failed')", name="ck_mc_status"),
        sa.ForeignKeyConstraint(["local_yolo_training_execution_run_id"], ["detection_training_execution_runs.id"]),
        sa.ForeignKeyConstraint(["detection_training_run_id"], ["detection_training_runs.id"]),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mc_local_run", "model_candidates", ["local_yolo_training_execution_run_id"])
    op.create_index("ix_mc_dt_run", "model_candidates", ["detection_training_run_id"])
    op.create_index("ix_mc_model_version", "model_candidates", ["model_version_id"])
    op.create_index("ix_mc_kind", "model_candidates", ["candidate_kind"])
    op.create_index("ix_mc_status", "model_candidates", ["status"])
    op.create_index("ix_mc_created_at", "model_candidates", ["created_at"])

    op.create_table(
        "model_evaluation_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("model_candidate_id", sa.UUID(), nullable=False),
        sa.Column("local_yolo_training_execution_run_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("metrics_summary", PortableJSON(), nullable=False),
        sa.Column("thresholds", PortableJSON(), nullable=False),
        sa.Column("dataset_summary", PortableJSON(), nullable=False),
        sa.Column("artifact_summary", PortableJSON(), nullable=False),
        sa.Column("evaluation_summary", PortableJSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("info_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'completed', 'failed', 'blocked')", name="ck_mer_status"),
        sa.CheckConstraint("decision IN ('smoke_only', 'not_evaluable', 'not_promotable', 'promotable_with_warnings', 'promotable', 'blocked_by_policy', 'failed_evaluation')", name="ck_mer_decision"),
        sa.ForeignKeyConstraint(["model_candidate_id"], ["model_candidates.id"]),
        sa.ForeignKeyConstraint(["local_yolo_training_execution_run_id"], ["detection_training_execution_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mer_candidate", "model_evaluation_runs", ["model_candidate_id"])
    op.create_index("ix_mer_local_run", "model_evaluation_runs", ["local_yolo_training_execution_run_id"])
    op.create_index("ix_mer_status", "model_evaluation_runs", ["status"])
    op.create_index("ix_mer_decision", "model_evaluation_runs", ["decision"])
    op.create_index("ix_mer_created_at", "model_evaluation_runs", ["created_at"])

    op.create_table(
        "model_evaluation_issues",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("model_evaluation_run_id", sa.UUID(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", PortableJSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('error', 'warning', 'info')", name="ck_mei_severity"),
        sa.ForeignKeyConstraint(["model_evaluation_run_id"], ["model_evaluation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mei_eval_run", "model_evaluation_issues", ["model_evaluation_run_id"])
    op.create_index("ix_mei_severity", "model_evaluation_issues", ["severity"])
    op.create_index("ix_mei_code", "model_evaluation_issues", ["code"])
    op.create_index("ix_mei_created_at", "model_evaluation_issues", ["created_at"])

    op.create_table(
        "model_promotion_gate_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("model_candidate_id", sa.UUID(), nullable=False),
        sa.Column("model_evaluation_run_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("gate_summary", PortableJSON(), nullable=False),
        sa.Column("blocking_reasons", PortableJSON(), nullable=False),
        sa.Column("required_thresholds", PortableJSON(), nullable=False),
        sa.Column("observed_metrics", PortableJSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("decision IN ('smoke_only', 'not_evaluable', 'not_promotable', 'promotable_with_warnings', 'promotable', 'blocked_by_policy', 'failed_evaluation')", name="ck_mpgr_decision"),
        sa.ForeignKeyConstraint(["model_candidate_id"], ["model_candidates.id"]),
        sa.ForeignKeyConstraint(["model_evaluation_run_id"], ["model_evaluation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mpgr_candidate", "model_promotion_gate_runs", ["model_candidate_id"])
    op.create_index("ix_mpgr_eval_run", "model_promotion_gate_runs", ["model_evaluation_run_id"])
    op.create_index("ix_mpgr_decision", "model_promotion_gate_runs", ["decision"])
    op.create_index("ix_mpgr_created_at", "model_promotion_gate_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_mpgr_created_at", table_name="model_promotion_gate_runs")
    op.drop_index("ix_mpgr_decision", table_name="model_promotion_gate_runs")
    op.drop_index("ix_mpgr_eval_run", table_name="model_promotion_gate_runs")
    op.drop_index("ix_mpgr_candidate", table_name="model_promotion_gate_runs")
    op.drop_table("model_promotion_gate_runs")
    op.drop_index("ix_mei_created_at", table_name="model_evaluation_issues")
    op.drop_index("ix_mei_code", table_name="model_evaluation_issues")
    op.drop_index("ix_mei_severity", table_name="model_evaluation_issues")
    op.drop_index("ix_mei_eval_run", table_name="model_evaluation_issues")
    op.drop_table("model_evaluation_issues")
    op.drop_index("ix_mer_created_at", table_name="model_evaluation_runs")
    op.drop_index("ix_mer_decision", table_name="model_evaluation_runs")
    op.drop_index("ix_mer_status", table_name="model_evaluation_runs")
    op.drop_index("ix_mer_local_run", table_name="model_evaluation_runs")
    op.drop_index("ix_mer_candidate", table_name="model_evaluation_runs")
    op.drop_table("model_evaluation_runs")
    op.drop_index("ix_mc_created_at", table_name="model_candidates")
    op.drop_index("ix_mc_status", table_name="model_candidates")
    op.drop_index("ix_mc_kind", table_name="model_candidates")
    op.drop_index("ix_mc_model_version", table_name="model_candidates")
    op.drop_index("ix_mc_dt_run", table_name="model_candidates")
    op.drop_index("ix_mc_local_run", table_name="model_candidates")
    op.drop_table("model_candidates")
