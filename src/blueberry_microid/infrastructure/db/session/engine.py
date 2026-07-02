from sqlalchemy import Engine, create_engine


def create_db_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Build the SQLAlchemy engine.

    PostgreSQL is the target database for every non-test environment; other
    dialects (e.g. SQLite) are only used by this project's integration
    tests, and only for the subset of tables that do not rely on
    Postgres-only column types (JSONB) — see tests/integration/db.
    """

    return create_engine(database_url, echo=echo, future=True)
