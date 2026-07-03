import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import (
    TrainingRunComparisonEntryModel,
    TrainingRunComparisonModel,
    TrainingRunModel,
)
from tests.integration.postgres.test_training_run_schema import _create_training_run_with_split_item

pytestmark = pytest.mark.postgres


def _create_second_training_run(pg_session, first_run: TrainingRunModel) -> TrainingRunModel:
    run = TrainingRunModel(
        dataset_release_id=first_run.dataset_release_id,
        preflight_run_id=first_run.preflight_run_id,
        run_kind="baseline",
        baseline_model_type="logistic_regression_tabular",
        status="completed",
        experiment_name=f"pg-classical-{uuid.uuid4()}",
        config={},
        baseline_state={"feature_names": ["petri__area"]},
        metrics={
            "accuracy_by_split": {"train": 1.0, "validation": 0.5, "test": 1.0},
            "support_by_split": {"train": 1, "validation": 0, "test": 1},
        },
        summary={"contains_deep_learning": False},
        started_at=first_run.started_at,
    )
    pg_session.add(run)
    pg_session.flush()
    return run


def _create_comparison(pg_session):
    first_run, _split_item, _dataset_item = _create_training_run_with_split_item(pg_session)
    first_run.metrics = {
        "accuracy_by_split": {"train": 1.0, "validation": 1.0, "test": 1.0},
        "support_by_split": {"train": 1, "validation": 0, "test": 1},
    }
    second_run = _create_second_training_run(pg_session, first_run)
    comparison = TrainingRunComparisonModel(
        dataset_release_id=first_run.dataset_release_id,
        name="pg-comparison",
        primary_metric="accuracy",
        primary_split="test",
        selection_policy="best_primary_metric",
        selected_training_run_id=first_run.id,
        comparison_summary={"selection_is_preliminary": True, "contains_deep_learning": False},
        warnings={"low_support": [{"training_run_id": str(first_run.id)}]},
    )
    pg_session.add(comparison)
    pg_session.flush()
    return comparison, first_run, second_run


def test_alembic_created_training_run_comparison_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('training_run_comparisons', 'training_run_comparison_entries')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["training_run_comparison_entries", "training_run_comparisons"]


def test_training_run_comparison_unique_constraint_per_comparison_and_run(pg_session):
    comparison, first_run, _second_run = _create_comparison(pg_session)
    first = TrainingRunComparisonEntryModel(
        comparison_id=comparison.id,
        training_run_id=first_run.id,
        rank=1,
        run_kind="baseline",
        baseline_model_type="majority_class",
        primary_metric_value=1.0,
        metrics_snapshot=first_run.metrics,
        summary={},
    )
    duplicate = TrainingRunComparisonEntryModel(
        comparison_id=comparison.id,
        training_run_id=first_run.id,
        rank=2,
        run_kind="baseline",
        baseline_model_type="majority_class",
        primary_metric_value=0.5,
        metrics_snapshot=first_run.metrics,
        summary={},
    )
    pg_session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_training_run_comparison_json_columns_round_trip_as_jsonb(pg_session):
    comparison, first_run, _second_run = _create_comparison(pg_session)
    entry = TrainingRunComparisonEntryModel(
        comparison_id=comparison.id,
        training_run_id=first_run.id,
        rank=1,
        run_kind="baseline",
        baseline_model_type="majority_class",
        primary_metric_value=1.0,
        metrics_snapshot=first_run.metrics,
        summary={"selection_is_preliminary": True},
    )
    pg_session.add(entry)
    pg_session.flush()
    pg_session.refresh(comparison)
    pg_session.refresh(entry)

    assert comparison.comparison_summary["contains_deep_learning"] is False
    assert comparison.warnings["low_support"][0]["training_run_id"] == str(first_run.id)
    assert entry.metrics_snapshot["accuracy_by_split"]["test"] == 1.0

    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'training_run_comparisons' AND column_name = 'comparison_summary'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_training_run_comparison_foreign_keys_are_enforced(pg_session):
    comparison, _first_run, _second_run = _create_comparison(pg_session)
    entry = TrainingRunComparisonEntryModel(
        comparison_id=comparison.id,
        training_run_id=uuid.uuid4(),
        rank=1,
        run_kind="baseline",
        baseline_model_type="majority_class",
        primary_metric_value=1.0,
        metrics_snapshot={},
        summary={},
    )
    pg_session.add(entry)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_training_run_comparison_check_constraints_reject_unknown_values(pg_session):
    first_run, _split_item, _dataset_item = _create_training_run_with_split_item(pg_session)
    comparison = TrainingRunComparisonModel(
        dataset_release_id=first_run.dataset_release_id,
        name="bad-primary-metric",
        primary_metric="f1",
        primary_split="test",
        selection_policy="best_primary_metric",
        comparison_summary={},
        warnings={},
    )
    pg_session.add(comparison)

    with pytest.raises(IntegrityError):
        pg_session.flush()
