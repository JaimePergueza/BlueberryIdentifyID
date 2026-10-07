"""Bind new reviews to accounts and preserve manual colony counts.

Historical reviewer names cannot prove account identity and are left unchanged.
"""

import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("human_reviews") as batch:
        batch.add_column(sa.Column("reviewer_user_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("reviewed_colony_count", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_human_reviews_reviewer_user_id", "users", ["reviewer_user_id"], ["id"])
        batch.create_index("ix_human_reviews_reviewer_user_id", ["reviewer_user_id"])
        batch.create_check_constraint(
            "ck_human_reviews_colony_count_range",
            "reviewed_colony_count IS NULL OR (reviewed_colony_count >= 0 AND reviewed_colony_count <= 100000)",
        )
        batch.create_check_constraint(
            "ck_human_reviews_invalid_sample_no_count",
            "review_decision != 'rejected_invalid_sample' OR reviewed_colony_count IS NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("human_reviews") as batch:
        batch.drop_constraint("ck_human_reviews_invalid_sample_no_count", type_="check")
        batch.drop_constraint("ck_human_reviews_colony_count_range", type_="check")
        batch.drop_index("ix_human_reviews_reviewer_user_id")
        batch.drop_constraint("fk_human_reviews_reviewer_user_id", type_="foreignkey")
        batch.drop_column("reviewed_colony_count")
        batch.drop_column("reviewer_user_id")
