"""Add curation provenance to dataset items

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa

from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dataset_items", sa.Column("curation_run_id", sa.UUID(), nullable=True))
    op.add_column("dataset_items", sa.Column("curation_item_id", sa.UUID(), nullable=True))
    op.add_column("dataset_items", sa.Column("provenance", PortableJSON(), nullable=True))
    op.create_foreign_key(
        "fk_ds_items_cur_run",
        "dataset_items",
        "dataset_curation_runs",
        ["curation_run_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_ds_items_cur_item",
        "dataset_items",
        "dataset_curation_items",
        ["curation_item_id"],
        ["id"],
    )
    op.create_index("ix_ds_items_cur_run_id", "dataset_items", ["curation_run_id"])
    op.create_index("ix_ds_items_cur_item_id", "dataset_items", ["curation_item_id"])


def downgrade() -> None:
    op.drop_index("ix_ds_items_cur_item_id", table_name="dataset_items")
    op.drop_index("ix_ds_items_cur_run_id", table_name="dataset_items")
    op.drop_constraint("fk_ds_items_cur_item", "dataset_items", type_="foreignkey")
    op.drop_constraint("fk_ds_items_cur_run", "dataset_items", type_="foreignkey")
    op.drop_column("dataset_items", "provenance")
    op.drop_column("dataset_items", "curation_item_id")
    op.drop_column("dataset_items", "curation_run_id")
