"""Add non-deep image feature extraction runs and vectors

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "image_feature_extraction_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_release_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_releases.id"),
            nullable=False,
        ),
        sa.Column(
            "image_audit_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("image_dataset_audit_runs.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("processed_items", sa.Integer(), nullable=False),
        sa.Column("failed_items", sa.Integer(), nullable=False),
        sa.Column("total_feature_vectors", sa.Integer(), nullable=False),
        sa.Column("petri_feature_count", sa.Integer(), nullable=False),
        sa.Column("micro_feature_count", sa.Integer(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('completed', 'failed', 'partial')", name="ck_image_feature_extraction_runs_status"
        ),
    )
    op.create_index(
        "ix_image_feature_extraction_runs_dataset_release_id",
        "image_feature_extraction_runs",
        ["dataset_release_id"],
    )
    op.create_index(
        "ix_image_feature_extraction_runs_image_audit_run_id",
        "image_feature_extraction_runs",
        ["image_audit_run_id"],
    )
    op.create_index(
        "ix_image_feature_extraction_runs_created_at", "image_feature_extraction_runs", ["created_at"]
    )

    op.create_table(
        "image_feature_vectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "feature_extraction_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("image_feature_extraction_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "dataset_release_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_releases.id"),
            nullable=False,
        ),
        sa.Column(
            "dataset_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_items.id"),
            nullable=False,
        ),
        sa.Column(
            "dataset_split_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_split_items.id"),
            nullable=False,
        ),
        sa.Column("split", sa.String(length=32), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("image_path", sa.Text(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("preprocessing", postgresql.JSONB(), nullable=False),
        sa.Column("extraction_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("split IN ('train', 'validation', 'test')", name="ck_image_feature_vectors_split"),
        sa.CheckConstraint("modality IN ('petri', 'micro')", name="ck_image_feature_vectors_modality"),
        sa.UniqueConstraint(
            "feature_extraction_run_id",
            "dataset_split_item_id",
            "modality",
            name="uq_image_feature_vectors_run_split_item_modality",
        ),
    )
    op.create_index(
        "ix_image_feature_vectors_feature_extraction_run_id",
        "image_feature_vectors",
        ["feature_extraction_run_id"],
    )
    op.create_index("ix_image_feature_vectors_dataset_release_id", "image_feature_vectors", ["dataset_release_id"])
    op.create_index("ix_image_feature_vectors_dataset_item_id", "image_feature_vectors", ["dataset_item_id"])
    op.create_index(
        "ix_image_feature_vectors_dataset_split_item_id", "image_feature_vectors", ["dataset_split_item_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_image_feature_vectors_dataset_split_item_id", table_name="image_feature_vectors")
    op.drop_index("ix_image_feature_vectors_dataset_item_id", table_name="image_feature_vectors")
    op.drop_index("ix_image_feature_vectors_dataset_release_id", table_name="image_feature_vectors")
    op.drop_index("ix_image_feature_vectors_feature_extraction_run_id", table_name="image_feature_vectors")
    op.drop_table("image_feature_vectors")

    op.drop_index("ix_image_feature_extraction_runs_created_at", table_name="image_feature_extraction_runs")
    op.drop_index(
        "ix_image_feature_extraction_runs_image_audit_run_id", table_name="image_feature_extraction_runs"
    )
    op.drop_index(
        "ix_image_feature_extraction_runs_dataset_release_id", table_name="image_feature_extraction_runs"
    )
    op.drop_table("image_feature_extraction_runs")
