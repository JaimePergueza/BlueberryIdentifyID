"""Fixtures for tests that require a REAL PostgreSQL database.

Unlike the rest of the suite (which uses SQLite for speed), these tests
validate behavior SQLite cannot represent faithfully: native ENUM types,
JSONB, partial unique indexes, CHECK constraints, and UUID columns. They
also apply the real Alembic migrations, so a green run here means the
migrations actually work against PostgreSQL — not just that `create_all`
would.

They are gated on a real `DATABASE_URL` environment variable pointing at
PostgreSQL. When it is absent (the normal case on a developer machine
without PostgreSQL), every test here is *skipped*, never failed — so
`pytest -v` stays green locally. In CI they run in the dedicated
`postgres-migrations` job, which sets `DATABASE_URL` to a real service
container. Nothing here uses SQLite as a stand-in.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[3]

# Ordered so a plain (non-CASCADE) reference would drop children first; with
# CASCADE the order is not strictly required, but keeping it explicit
# documents the dependency graph.
_ALL_TABLES = (
    "detection_training_issues",
    "detection_training_runs",
    "annotation_quality_gate_issues",
    "annotation_quality_gate_runs",
    "annotation_bundle_files",
    "annotation_bundle_runs",
    "petri_annotation_export_items",
    "petri_annotation_export_runs",
    "petri_region_reviews",
    "petri_segmentation_regions",
    "petri_segmentation_runs",
    "image_feature_vectors",
    "image_feature_extraction_runs",
    "image_dataset_audit_issues",
    "image_dataset_audit_runs",
    "training_predictions",
    "training_runs",
    "training_preflight_issues",
    "training_preflight_runs",
    "dataset_split_items",
    "dataset_releases",
    "dataset_items",
    "dataset_snapshots",
    "human_reviews",
    "predictions",
    "analysis_runs",
    "micro_images",
    "petri_images",
    "model_versions",
    "samples",
)


def _configured_postgres_url() -> str | None:
    """The DATABASE_URL env var, but only if it points at PostgreSQL.

    Deliberately reads the raw environment variable rather than `Settings`
    (whose default is a PostgreSQL URL even when nothing is configured) — so
    the gate is "did someone explicitly provide a PostgreSQL database?", not
    "does the default happen to look like PostgreSQL?".
    """
    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgresql"):
        return url
    return None


@pytest.fixture(scope="session")
def postgres_url() -> str:
    url = _configured_postgres_url()
    if url is None:
        pytest.skip(
            "PostgreSQL not configured: set DATABASE_URL=postgresql+psycopg://... "
            "to run these tests (they run in the 'postgres-migrations' CI job)."
        )
    return url


@pytest.fixture(scope="session")
def migrated_engine(postgres_url):
    """Apply the real Alembic migrations to the real database, then hand back
    an engine bound to it. Starts from a clean slate (downgrade to base) so a
    prior run's leftover schema never masks a broken migration.
    """
    from alembic import command
    from alembic.config import Config

    # alembic/env.py reads DATABASE_URL from the environment; make sure the
    # subprocess-free (in-process) command call sees the same target.
    os.environ["DATABASE_URL"] = postgres_url

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


def _truncate_all(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE " + ", ".join(_ALL_TABLES) + " RESTART IDENTITY CASCADE")
        )


@pytest.fixture()
def pg_session(migrated_engine):
    """A session on the migrated PostgreSQL database, with every row removed
    after the test so cases stay isolated. Rolls back first, so a test that
    triggered a constraint error (leaving its transaction aborted) does not
    break the truncate.
    """
    session = Session(migrated_engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        _truncate_all(migrated_engine)
