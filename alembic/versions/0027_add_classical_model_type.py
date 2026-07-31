"""Add classical image-processing engine type.

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-30

The PostgreSQL enum value is intentionally retained on downgrade. PostgreSQL
cannot safely remove an enum value in place without rebuilding dependent
columns. A complete downgrade to base still drops and recreates the enum via
the earlier schema migrations.
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE model_type ADD VALUE IF NOT EXISTS 'classical'")


def downgrade() -> None:
    # Deliberate no-op; see module docstring.
    pass
