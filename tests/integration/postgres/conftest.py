"""Fixtures for tests that require a REAL PostgreSQL database."""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[3]

# Children precede parents so the list also documents the dependency graph.
_ALL_TABLES = (
    "auth_sessions",
    "users",
    "model_promotion_gate_runs",
    "model_evaluation_issues",
    "model_evaluation_runs",
    "model_candidates",
    "detection_training_execution_issues",
    "detection_training_execution_runs",
    "detection_training_artifact_issues",
    "detection_training_artifact_records",
    "detection_training_artifact_policies",
    "detection_training_environment_issues",
    "detection_training_environment_specs",
    "detection_training_readiness_issues",
    "detection_training_readiness_reports",
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
    "dataset_curation_items",
    "dataset_curation_runs",
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
    """Apply the complete migration chain to a clean PostgreSQL database."""
    from alembic import command
    from alembic.config import Config

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
    session = Session(migrated_engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        _truncate_all(migrated_engine)
