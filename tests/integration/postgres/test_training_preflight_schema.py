import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import TrainingPreflightIssueModel, TrainingPreflightRunModel
from tests.integration.postgres.test_dataset_release_schema import _create_dataset_item, _create_release

pytestmark = pytest.mark.postgres


def _create_preflight_run(pg_session, **overrides) -> TrainingPreflightRunModel:
    item = _create_dataset_item(pg_session, sample_code=f"S-PG-PREFLIGHT-{uuid.uuid4()}")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    defaults = dict(
        dataset_release_id=release.id,
        status="passed",
        is_valid=True,
        config={"experiment_name": "pg-preflight", "output_dir": "out"},
        summary={"error_count": 0, "warning_count": 0, "contains_model_metrics": False},
        item_count=1,
        train_count=0,
        validation_count=0,
        test_count=1,
        label_counts={"suspicious_growth": 1},
        split_counts={"test": 1},
        split_label_counts={"test": {"suspicious_growth": 1}},
        leakage_checks={"sample_split_isolation": True},
    )
    defaults.update(overrides)
    run = TrainingPreflightRunModel(**defaults)
    pg_session.add(run)
    pg_session.flush()
    return run


def test_alembic_created_training_preflight_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('training_preflight_runs', 'training_preflight_issues')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["training_preflight_issues", "training_preflight_runs"]


def test_training_preflight_status_check_rejects_unknown_value(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-PREFLIGHT-BADSTATUS")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    run = TrainingPreflightRunModel(
        dataset_release_id=release.id,
        status="running",
        is_valid=True,
        config={},
        summary={},
        item_count=0,
        train_count=0,
        validation_count=0,
        test_count=0,
        label_counts={},
        split_counts={},
        split_label_counts={},
        leakage_checks={},
    )
    pg_session.add(run)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_training_preflight_issue_severity_check_rejects_unknown_value(pg_session):
    run = _create_preflight_run(pg_session)
    issue = TrainingPreflightIssueModel(
        preflight_run_id=run.id,
        severity="info",
        code="not_allowed",
        message="not allowed",
    )
    pg_session.add(issue)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_training_preflight_json_columns_round_trip_as_jsonb(pg_session):
    run = _create_preflight_run(
        pg_session,
        config={"experiment_name": "pg-json", "batch_size": 8},
        summary={"error_count": 0, "warning_count": 1, "contains_model_metrics": False},
    )
    pg_session.refresh(run)

    assert run.config["experiment_name"] == "pg-json"
    assert run.summary["contains_model_metrics"] is False

    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'training_preflight_runs' AND column_name = 'config'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_training_preflight_run_foreign_key_to_dataset_release_is_enforced(pg_session):
    run = TrainingPreflightRunModel(
        dataset_release_id=uuid.uuid4(),
        status="failed",
        is_valid=False,
        config={},
        summary={},
        item_count=0,
        train_count=0,
        validation_count=0,
        test_count=0,
        label_counts={},
        split_counts={},
        split_label_counts={},
        leakage_checks={},
    )
    pg_session.add(run)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_training_preflight_issue_foreign_key_to_run_is_enforced(pg_session):
    issue = TrainingPreflightIssueModel(
        preflight_run_id=uuid.uuid4(),
        severity="error",
        code="manifest_validation_error",
        message="missing split",
    )
    pg_session.add(issue)

    with pytest.raises(IntegrityError):
        pg_session.flush()
