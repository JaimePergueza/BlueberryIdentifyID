"""Cross-dialect column types shared by ORM models.

`predictions.class_probabilities` needs a JSON column. PostgreSQL's `JSONB`
is the right choice for the real database (indexable, binary-stored), but it
cannot be compiled for SQLite — which this project's own test suite uses for
speed (see tests/integration/db/ and tests/api/). `PortableJSON` resolves to
`JSONB` on PostgreSQL and to SQLAlchemy's generic `JSON` (which SQLite
supports) everywhere else, so the exact same model works against both
without weakening the real schema: the DDL PostgreSQL sees is unchanged
(still `JSONB`), so no Alembic migration is needed for this — the existing
`0001_initial_schema.py` migration remains correct as-is.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator


class PortableJSON(TypeDecorator):
    """JSONB on PostgreSQL, generic JSON on every other dialect (e.g. SQLite)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())
