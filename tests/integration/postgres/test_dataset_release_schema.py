import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.models import (
    DatasetItemModel,
    DatasetReleaseModel,
    DatasetSnapshotModel,
    DatasetSplitItemModel,
    HumanReviewModel,
    PredictionModel,
)
from tests.integration.postgres._factories import create_analysis_run

pytestmark = pytest.mark.postgres


def _create_dataset_item(session, sample_code: str = "S-PG-RELEASE-1") -> DatasetItemModel:
    """Build a full, valid dataset_item row (and its snapshot) for release
    tests to attach split items to."""
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

    snapshot = DatasetSnapshotModel(name=f"pg-release-{sample_code}", version="0.1.0", item_count=1)
    session.add(snapshot)
    session.flush()

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
    session.add(item)
    session.flush()
    return item


def _create_release(session, dataset_snapshot_id, **overrides) -> DatasetReleaseModel:
    defaults = dict(
        dataset_snapshot_id=dataset_snapshot_id,
        name="pg-release",
        version="0.1.0",
        split_strategy="by_sample",
        random_seed=42,
        train_ratio=0.70,
        validation_ratio=0.15,
        test_ratio=0.15,
    )
    defaults.update(overrides)
    release = DatasetReleaseModel(**defaults)
    session.add(release)
    session.flush()
    return release


def test_alembic_created_dataset_release_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('dataset_releases', 'dataset_split_items')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["dataset_releases", "dataset_split_items"]


def test_dataset_split_item_unique_constraint_per_release_and_item(pg_session):
    item = _create_dataset_item(pg_session)
    release = _create_release(pg_session, item.dataset_snapshot_id)

    first = DatasetSplitItemModel(
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        sample_id=item.sample_id,
        split=DatasetSplit.TEST,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
    )
    duplicate = DatasetSplitItemModel(
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        sample_id=item.sample_id,
        split=DatasetSplit.TRAIN,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
    )
    pg_session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_dataset_release_json_distributions_round_trip_as_jsonb(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-RELEASE-JSON")
    release = _create_release(
        pg_session,
        item.dataset_snapshot_id,
        item_count=1,
        train_count=0,
        validation_count=0,
        test_count=1,
        label_distribution={"suspicious_growth": 1},
        split_distribution={"test": {"suspicious_growth": 1}},
    )
    pg_session.refresh(release)

    assert release.label_distribution["suspicious_growth"] == 1
    assert release.split_distribution["test"]["suspicious_growth"] == 1

    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'dataset_releases' AND column_name = 'split_distribution'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_dataset_split_enum_stores_values_not_python_member_names(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-RELEASE-ENUM")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    split_item = DatasetSplitItemModel(
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        sample_id=item.sample_id,
        split=DatasetSplit.VALIDATION,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
    )
    pg_session.add(split_item)
    pg_session.flush()

    stored = pg_session.execute(
        text("SELECT split::text FROM dataset_split_items WHERE id = :id"),
        {"id": split_item.id},
    ).scalar_one()
    assert stored == "validation"


def test_dataset_split_item_foreign_keys_are_enforced(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-RELEASE-FK")
    bogus_id = uuid.uuid4()
    split_item = DatasetSplitItemModel(
        dataset_release_id=bogus_id,
        dataset_item_id=item.id,
        sample_id=item.sample_id,
        split=DatasetSplit.TRAIN,
    )
    pg_session.add(split_item)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_dataset_release_foreign_key_to_snapshot_is_enforced(pg_session):
    release = DatasetReleaseModel(
        dataset_snapshot_id=uuid.uuid4(),
        name="pg-orphan-release",
        version="0.1.0",
        split_strategy="by_sample",
        random_seed=1,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
    )
    pg_session.add(release)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_dataset_release_split_strategy_check_constraint_rejects_unknown_value(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-RELEASE-BADSTRATEGY")
    release = DatasetReleaseModel(
        dataset_snapshot_id=item.dataset_snapshot_id,
        name="pg-bad-strategy-release",
        version="0.1.0",
        split_strategy="not_a_real_strategy",
        random_seed=1,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
    )
    pg_session.add(release)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_dataset_release_persists_with_by_lot_strategy(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-RELEASE-BYLOT")

    release = _create_release(pg_session, item.dataset_snapshot_id, split_strategy="by_lot")
    pg_session.refresh(release)

    stored = pg_session.execute(
        text("SELECT split_strategy FROM dataset_releases WHERE id = :id"),
        {"id": release.id},
    ).scalar_one()
    assert stored == "by_lot"


def test_dataset_release_persists_with_by_origin_lot_strategy(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-RELEASE-BYORIGINLOT")

    release = _create_release(pg_session, item.dataset_snapshot_id, split_strategy="by_origin_lot")
    pg_session.refresh(release)

    stored = pg_session.execute(
        text("SELECT split_strategy FROM dataset_releases WHERE id = :id"),
        {"id": release.id},
    ).scalar_one()
    assert stored == "by_origin_lot"


def test_dataset_release_persists_snapshot_release_metadata(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-SNAPSHOT-RELEASE")
    manifest = {
        "dataset_snapshot_id": str(item.dataset_snapshot_id),
        "items": [{"dataset_item_id": str(item.id), "ground_truth_label": "suspicious_growth"}],
    }

    release = _create_release(
        pg_session,
        item.dataset_snapshot_id,
        release_kind="snapshot_release",
        status="completed",
        description="metadata-only release",
        item_count=1,
        train_count=0,
        validation_count=0,
        test_count=0,
        label_distribution={"suspicious_growth": 1},
        split_distribution=None,
        manifest=manifest,
        provenance={"eligible_item_count": 1, "skipped_item_count": 0, "split_oriented": False},
    )
    pg_session.refresh(release)

    stored = pg_session.execute(
        text(
            "SELECT release_kind, status, description, manifest, provenance "
            "FROM dataset_releases WHERE id = :id"
        ),
        {"id": release.id},
    ).one()

    assert stored.release_kind == "snapshot_release"
    assert stored.status == "completed"
    assert stored.description == "metadata-only release"
    assert stored.manifest == manifest
    assert stored.provenance["eligible_item_count"] == 1
    assert stored.provenance["skipped_item_count"] == 0
    assert stored.provenance["split_oriented"] is False


def test_dataset_release_release_kind_check_constraint_rejects_unknown_value(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-RELEASE-BADKIND")
    release = DatasetReleaseModel(
        dataset_snapshot_id=item.dataset_snapshot_id,
        name="pg-bad-kind-release",
        version="0.1.0",
        release_kind="not_a_real_release_kind",
        status="completed",
        split_strategy="by_sample",
        random_seed=1,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
    )
    pg_session.add(release)

    with pytest.raises(IntegrityError):
        pg_session.flush()
