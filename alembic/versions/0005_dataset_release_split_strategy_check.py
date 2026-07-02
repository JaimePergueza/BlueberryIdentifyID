"""Constrain dataset_releases.split_strategy to the three supported values

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-04

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHECK_NAME = "ck_dataset_releases_split_strategy"
_CHECK_SQL = "split_strategy IN ('by_sample', 'by_lot', 'by_origin_lot')"


def upgrade() -> None:
    # Fase 9 only ever wrote "random_by_sample" (the sole strategy that
    # existed then) into this free-text column. It is semantically
    # identical to today's `by_sample` — every item was already grouped by
    # sample_id — so existing rows are normalized before the constraint
    # goes on, instead of being left to violate it.
    op.execute("UPDATE dataset_releases SET split_strategy = 'by_sample' WHERE split_strategy = 'random_by_sample'")
    op.create_check_constraint(_CHECK_NAME, "dataset_releases", _CHECK_SQL)


def downgrade() -> None:
    op.drop_constraint(_CHECK_NAME, "dataset_releases", type_="check")
