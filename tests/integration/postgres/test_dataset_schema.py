import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.models import DatasetItemModel, DatasetSnapshotModel, HumanReviewModel, PredictionModel
from tests.integration.postgres._factories import create_analysis_run

pytestmark = pytest.mark.postgres


def _create_reviewed_run(session, sample_code: str = "S-PG-DATASET-1"):
    run = create_analysis_run(session, sample_code=sample_code)
    run.status = AnalysisStatus.COMPLETED
    prediction = PredictionModel(
        analysis_run_id=run.id,
        predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
        confidence_score=0.5,
    )
    session.add(prediction)
    session.flush()
    review = HumanReviewModel(
        analysis_run_id=run.id,
        reviewer_name="expert",
        review_decision=ReviewDecision.CONFIRMED,
        is_final=True,
    )
    session.add(review)
    session.flush()
    return run, prediction, review


def test_alembic_created_dataset_tables(pg_session):
    rows = pg_session.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('dataset_snapshots', 'dataset_items')
            ORDER BY table_name
            """
        )
    ).scalars().all()

    assert rows == ["dataset_items", "dataset_snapshots"]


def test_dataset_item_unique_constraint_per_snapshot_and_analysis_run(pg_session):
    run, prediction, review = _create_reviewed_run(pg_session)
    snapshot = DatasetSnapshotModel(
        name="pg-curated",
        version="0.1.0",
        item_count=1,
        label_distribution={"suspicious_growth": 1},
    )
    pg_session.add(snapshot)
    pg_session.flush()
    item = DatasetItemModel(
        dataset_snapshot_id=snapshot.id,
        analysis_run_id=run.id,
        sample_id=run.sample_id,
        petri_image_id=run.petri_image_id,
        micro_image_id=run.micro_image_id,
        prediction_id=prediction.id,
        final_review_id=review.id,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
        source_review_decision=ReviewDecision.CONFIRMED,
    )
    duplicate = DatasetItemModel(
        dataset_snapshot_id=snapshot.id,
        analysis_run_id=run.id,
        sample_id=run.sample_id,
        petri_image_id=run.petri_image_id,
        micro_image_id=run.micro_image_id,
        prediction_id=prediction.id,
        final_review_id=review.id,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
        source_review_decision=ReviewDecision.CONFIRMED,
    )
    pg_session.add_all([item, duplicate])

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_dataset_snapshot_label_distribution_round_trips_as_jsonb(pg_session):
    snapshot = DatasetSnapshotModel(
        name="pg-json",
        version="0.1.0",
        item_count=2,
        label_distribution={"no_evident_growth": 1, "suspicious_growth": 1},
    )
    pg_session.add(snapshot)
    pg_session.flush()
    pg_session.refresh(snapshot)

    assert snapshot.label_distribution["suspicious_growth"] == 1


def test_dataset_item_foreign_keys_are_enforced(pg_session):
    snapshot = DatasetSnapshotModel(name="pg-fk", version="0.1.0")
    pg_session.add(snapshot)
    pg_session.flush()
    item = DatasetItemModel(
        dataset_snapshot_id=snapshot.id,
        analysis_run_id=snapshot.id,
        sample_id=snapshot.id,
        petri_image_id=snapshot.id,
        micro_image_id=snapshot.id,
        prediction_id=snapshot.id,
        final_review_id=snapshot.id,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
        source_review_decision=ReviewDecision.CONFIRMED,
    )
    pg_session.add(item)

    with pytest.raises(IntegrityError):
        pg_session.flush()

