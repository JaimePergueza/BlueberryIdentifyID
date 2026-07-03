"""Add persistent image dataset audit reports

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "image_dataset_audit_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_release_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_releases.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_passed", sa.Boolean(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("total_petri_images", sa.Integer(), nullable=False),
        sa.Column("total_micro_images", sa.Integer(), nullable=False),
        sa.Column("checked_petri_images", sa.Integer(), nullable=False),
        sa.Column("checked_micro_images", sa.Integer(), nullable=False),
        sa.Column("failed_petri_images", sa.Integer(), nullable=False),
        sa.Column("failed_micro_images", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("format_distribution", postgresql.JSONB(), nullable=False),
        sa.Column("color_mode_distribution", postgresql.JSONB(), nullable=False),
        sa.Column("dimension_distribution", postgresql.JSONB(), nullable=False),
        sa.Column("file_size_distribution", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('passed', 'failed', 'warning')", name="ck_image_dataset_audit_runs_status"),
    )
    op.create_index(
        "ix_image_dataset_audit_runs_dataset_release_id",
        "image_dataset_audit_runs",
        ["dataset_release_id"],
    )
    op.create_index("ix_image_dataset_audit_runs_created_at", "image_dataset_audit_runs", ["created_at"])

    op.create_table(
        "image_dataset_audit_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("image_dataset_audit_runs.id"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column(
            "dataset_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_items.id"),
            nullable=True,
        ),
        sa.Column(
            "dataset_split_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_split_items.id"),
            nullable=True,
        ),
        sa.Column("image_path", sa.Text(), nullable=True),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('error', 'warning')", name="ck_image_dataset_audit_issues_severity"),
        sa.CheckConstraint("modality IN ('petri', 'micro')", name="ck_image_dataset_audit_issues_modality"),
    )
    op.create_index(
        "ix_image_dataset_audit_issues_audit_run_id",
        "image_dataset_audit_issues",
        ["audit_run_id"],
    )
    op.create_index("ix_image_dataset_audit_issues_created_at", "image_dataset_audit_issues", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_image_dataset_audit_issues_created_at", table_name="image_dataset_audit_issues")
    op.drop_index("ix_image_dataset_audit_issues_audit_run_id", table_name="image_dataset_audit_issues")
    op.drop_table("image_dataset_audit_issues")
    op.drop_index("ix_image_dataset_audit_runs_created_at", table_name="image_dataset_audit_runs")
    op.drop_index("ix_image_dataset_audit_runs_dataset_release_id", table_name="image_dataset_audit_runs")
    op.drop_table("image_dataset_audit_runs")
