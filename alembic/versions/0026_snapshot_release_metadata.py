"""Add metadata-only snapshot release fields

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa

from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dataset_releases",
        sa.Column("release_kind", sa.String(length=64), nullable=False, server_default="split_release"),
    )
    op.add_column(
        "dataset_releases",
        sa.Column("status", sa.String(length=64), nullable=False, server_default="completed"),
    )
    op.add_column("dataset_releases", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("dataset_releases", sa.Column("manifest", PortableJSON(), nullable=True))
    op.add_column("dataset_releases", sa.Column("provenance", PortableJSON(), nullable=True))
    op.create_check_constraint(
        "ck_dataset_releases_release_kind",
        "dataset_releases",
        "release_kind IN ('split_release', 'snapshot_release')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_dataset_releases_release_kind", "dataset_releases", type_="check")
    op.drop_column("dataset_releases", "provenance")
    op.drop_column("dataset_releases", "manifest")
    op.drop_column("dataset_releases", "description")
    op.drop_column("dataset_releases", "status")
    op.drop_column("dataset_releases", "release_kind")
