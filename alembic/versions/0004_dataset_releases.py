"""Add dataset releases and deterministic train/validation/test splits

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Already created by migration 0001; referenced here without create_type so
# it is not recreated.
predicted_label_enum = postgresql.ENUM(
    "no_evident_growth",
    "suspicious_growth",
    "probable_fungal_growth",
    "probable_bacterial_growth",
    "inconclusive",
    name="predicted_label",
    create_type=False,
)
# Brand new enum introduced by this migration — created explicitly below,
# same pattern as the enums in 0001.
dataset_split_enum = postgresql.ENUM(
    "train",
    "validation",
    "test",
    name="dataset_split",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    dataset_split_enum.create(bind, checkfirst=True)

    op.create_table(
        "dataset_releases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_snapshots.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("split_strategy", sa.String(length=64), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("train_ratio", sa.Float(), nullable=False),
        sa.Column("validation_ratio", sa.Float(), nullable=False),
        sa.Column("test_ratio", sa.Float(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("train_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("test_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label_distribution", postgresql.JSONB(), nullable=True),
        sa.Column("split_distribution", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_dataset_releases_dataset_snapshot_id", "dataset_releases", ["dataset_snapshot_id"])

    op.create_table(
        "dataset_split_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
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
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("samples.id"), nullable=False),
        sa.Column("split", dataset_split_enum, nullable=False),
        sa.Column("ground_truth_label", predicted_label_enum, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "dataset_release_id",
            "dataset_item_id",
            name="uq_dataset_split_items_release_item",
        ),
    )
    op.create_index("ix_dataset_split_items_dataset_release_id", "dataset_split_items", ["dataset_release_id"])
    op.create_index("ix_dataset_split_items_dataset_item_id", "dataset_split_items", ["dataset_item_id"])


def downgrade() -> None:
    op.drop_index("ix_dataset_split_items_dataset_item_id", table_name="dataset_split_items")
    op.drop_index("ix_dataset_split_items_dataset_release_id", table_name="dataset_split_items")
    op.drop_table("dataset_split_items")
    op.drop_index("ix_dataset_releases_dataset_snapshot_id", table_name="dataset_releases")
    op.drop_table("dataset_releases")

    bind = op.get_bind()
    dataset_split_enum.drop(bind, checkfirst=True)
