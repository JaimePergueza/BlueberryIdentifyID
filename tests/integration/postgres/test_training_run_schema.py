import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.db.models import DatasetSplitItemModel, TrainingPredictionModel, TrainingRunModel
from tests.integration.postgres.test_dataset_release_schema import _create_dataset_item, _create_release
from tests.integration.postgres.test_training_preflight_schema import _create_preflight_run

pytestmark = pytest.mark.postgres


def _create_training_run_with_split_item(pg_session):
    item = _create_dataset_item(pg_session, sample_code=f"S-PG-TRAINING-{uuid.uuid4()}")
    release = _create_release(
        pg_session,
        item.dataset_snapshot_id,
        item_count=1,
        train_count=1,
        validation_count=0,
        test_count=0,
    )
    split_item = DatasetSplitItemModel(
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        sample_id=item.sample_id,
        split=DatasetSplit.TRAIN,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
    )
    pg_session.add(split_item)
    pg_session.flush()
    preflight = _create_preflight_run(pg_session, dataset_release_id=release.id)
    run = TrainingRunModel(
        dataset_release_id=release.id,
        preflight_run_id=preflight.id,
        run_kind="baseline",
        baseline_model_type="majority_class",
        status="completed",
        experiment_name="pg-majority-baseline",
        config={"experiment_name": "pg-majority-baseline", "output_dir": "out"},
        baseline_state={"majority_label": "suspicious_growth"},
        metrics={"accuracy_overall": 1.0},
        summary={"uses_image_pixels": False},
        started_at=datetime.now(timezone.utc),
    )
    pg_session.add(run)
    pg_session.flush()
    return run, split_item, item


def test_alembic_created_training_run_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('training_runs', 'training_predictions')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["training_predictions", "training_runs"]


def test_training_prediction_unique_constraint_per_run_and_split_item(pg_session):
    run, split_item, dataset_item = _create_training_run_with_split_item(pg_session)
    first = TrainingPredictionModel(
        training_run_id=run.id,
        dataset_split_item_id=split_item.id,
        dataset_item_id=dataset_item.id,
        split=DatasetSplit.TRAIN,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
        predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
        is_correct=True,
    )
    duplicate = TrainingPredictionModel(
        training_run_id=run.id,
        dataset_split_item_id=split_item.id,
        dataset_item_id=dataset_item.id,
        split=DatasetSplit.TRAIN,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
        predicted_label=PredictedLabel.NO_EVIDENT_GROWTH,
        is_correct=False,
    )
    pg_session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_training_run_json_columns_round_trip_as_jsonb(pg_session):
    run, _split_item, _dataset_item = _create_training_run_with_split_item(pg_session)
    pg_session.refresh(run)

    assert run.baseline_state["majority_label"] == "suspicious_growth"
    assert run.metrics["accuracy_overall"] == 1.0
    assert run.summary["uses_image_pixels"] is False

    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'training_runs' AND column_name = 'metrics'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_training_run_accepts_logistic_regression_tabular_baseline_type(pg_session):
    item = _create_dataset_item(pg_session, sample_code=f"S-PG-TRAINING-CLASSICAL-{uuid.uuid4()}")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    preflight = _create_preflight_run(pg_session, dataset_release_id=release.id)
    run = TrainingRunModel(
        dataset_release_id=release.id,
        preflight_run_id=preflight.id,
        run_kind="baseline",
        baseline_model_type="logistic_regression_tabular",
        status="completed",
        experiment_name="pg-classical-baseline",
        config={"feature_extraction_run_id": str(uuid.uuid4())},
        baseline_state={"feature_names": ["petri__intensity__mean_intensity"]},
        metrics={"accuracy_overall": 1.0},
        summary={"uses_image_feature_vectors": True, "uses_image_pixels": False},
        started_at=datetime.now(timezone.utc),
    )
    pg_session.add(run)
    pg_session.flush()

    pg_session.refresh(run)
    assert run.baseline_model_type == "logistic_regression_tabular"
    assert run.baseline_state["feature_names"] == ["petri__intensity__mean_intensity"]


def test_training_prediction_foreign_keys_are_enforced(pg_session):
    _run, split_item, dataset_item = _create_training_run_with_split_item(pg_session)
    prediction = TrainingPredictionModel(
        training_run_id=uuid.uuid4(),
        dataset_split_item_id=split_item.id,
        dataset_item_id=dataset_item.id,
        split=DatasetSplit.TRAIN,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
        predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
        is_correct=True,
    )
    pg_session.add(prediction)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_training_run_check_constraints_reject_unknown_values(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-TRAINING-BADSTATUS")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    preflight = _create_preflight_run(pg_session, dataset_release_id=release.id)
    run = TrainingRunModel(
        dataset_release_id=release.id,
        preflight_run_id=preflight.id,
        run_kind="deep_learning",
        baseline_model_type="majority_class",
        status="completed",
        experiment_name="not-allowed",
        config={},
        baseline_state={},
        metrics={},
        summary={},
        started_at=datetime.now(timezone.utc),
    )
    pg_session.add(run)

    with pytest.raises(IntegrityError):
        pg_session.flush()
