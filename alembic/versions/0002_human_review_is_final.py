"""Add human_reviews.is_final and a partial unique index enforcing at most
one final review per analysis_run.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "human_reviews",
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index(
        "uq_human_reviews_one_final_per_run",
        "human_reviews",
        ["analysis_run_id"],
        unique=True,
        postgresql_where=sa.text("is_final = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_human_reviews_one_final_per_run", table_name="human_reviews")
    op.drop_column("human_reviews", "is_final")
