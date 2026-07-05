"""Add explanation and feature fields to predictions table

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa

from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("explanation", sa.Text(), nullable=True))
    op.add_column("predictions", sa.Column("feature_summary", PortableJSON, nullable=True))
    op.add_column("predictions", sa.Column("quality_summary", PortableJSON, nullable=True))
    op.add_column("predictions", sa.Column("decision_trace", PortableJSON, nullable=True))
    op.add_column("predictions", sa.Column("warnings", PortableJSON, nullable=True))


def downgrade() -> None:
    op.drop_column("predictions", "warnings")
    op.drop_column("predictions", "decision_trace")
    op.drop_column("predictions", "quality_summary")
    op.drop_column("predictions", "feature_summary")
    op.drop_column("predictions", "explanation")
