"""Schema-level checks against a REAL PostgreSQL database.

Validates the things SQLite cannot: that Alembic actually creates every
table, that JSONB round-trips (and supports JSONB operators), that native
ENUM columns store the enum *value* (not the Python member name), and that
UUID columns behave as real uuids.
"""

import uuid

import pytest
from sqlalchemy import inspect, text

from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.db.models import PredictionModel
from tests.integration.postgres._factories import create_analysis_run, create_model_version

pytestmark = pytest.mark.postgres

_EXPECTED_TABLES = {
    "samples",
    "petri_images",
    "micro_images",
    "model_versions",
    "analysis_runs",
    "predictions",
    "human_reviews",
}


def test_alembic_created_all_expected_tables(migrated_engine):
    inspector = inspect(migrated_engine)
    actual = set(inspector.get_table_names())
    missing = _EXPECTED_TABLES - actual
    assert not missing, f"migrations did not create: {missing}"


def test_prediction_class_probabilities_round_trips_through_jsonb(pg_session):
    run = create_analysis_run(pg_session, sample_code="S-PG-JSONB")
    probabilities = {"no_evident_growth": 0.6, "suspicious_growth": 0.4}
    prediction = PredictionModel(
        analysis_run_id=run.id,
        predicted_label=PredictedLabel.NO_EVIDENT_GROWTH,
        confidence_score=0.6,
        class_probabilities=probabilities,
    )
    pg_session.add(prediction)
    pg_session.commit()
    pg_session.expire_all()

    reloaded = pg_session.get(PredictionModel, prediction.id)
    assert reloaded.class_probabilities == probabilities

    # Prove it is genuine JSONB, not a text blob: the ->> operator must work.
    value = pg_session.execute(
        text("SELECT class_probabilities->>'no_evident_growth' FROM predictions WHERE id = :id"),
        {"id": prediction.id},
    ).scalar_one()
    assert value == "0.6"

    # And the column's real type on the server must be jsonb.
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'predictions' AND column_name = 'class_probabilities'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_enum_columns_store_values_not_python_member_names(pg_session):
    # ModelType.MOCK.value == "mock" (member name is "MOCK"); the column must
    # hold the value.
    model_version = create_model_version(pg_session, name="enum-check")
    pg_session.commit()

    stored = pg_session.execute(
        text("SELECT model_type::text FROM model_versions WHERE id = :id"),
        {"id": model_version.id},
    ).scalar_one()
    assert stored == "mock"


def test_analysis_status_enum_default_is_pending_value(pg_session):
    run = create_analysis_run(pg_session, sample_code="S-PG-ENUM")
    pg_session.commit()

    stored = pg_session.execute(
        text("SELECT status::text FROM analysis_runs WHERE id = :id"),
        {"id": run.id},
    ).scalar_one()
    assert stored == AnalysisStatus.PENDING.value == "pending"


def test_uuid_columns_are_real_uuids(pg_session):
    run = create_analysis_run(pg_session, sample_code="S-PG-UUID")
    pg_session.commit()

    returned_id = pg_session.execute(
        text("SELECT id FROM analysis_runs WHERE id = :id"),
        {"id": run.id},
    ).scalar_one()
    # psycopg returns a real uuid.UUID for a uuid column, equal to what we
    # inserted — not a string that merely looks like one.
    assert isinstance(returned_id, uuid.UUID)
    assert returned_id == run.id
