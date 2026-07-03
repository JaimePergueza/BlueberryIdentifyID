"""Allow classical tabular baseline training runs

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_training_runs_baseline_model_type", "training_runs", type_="check")
    op.create_check_constraint(
        "ck_training_runs_baseline_model_type",
        "training_runs",
        "baseline_model_type IN ('majority_class', 'logistic_regression_tabular')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_training_runs_baseline_model_type", "training_runs", type_="check")
    op.create_check_constraint(
        "ck_training_runs_baseline_model_type",
        "training_runs",
        "baseline_model_type IN ('majority_class')",
    )
