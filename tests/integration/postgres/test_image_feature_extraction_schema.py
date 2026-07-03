import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.db.models import (
    DatasetSplitItemModel,
    ImageFeatureExtractionRunModel,
    ImageFeatureVectorModel,
)
from tests.integration.postgres.test_dataset_release_schema import _create_dataset_item, _create_release
from tests.integration.postgres.test_image_dataset_audit_schema import _create_audit_run

pytestmark = pytest.mark.postgres


def _create_extraction_run(pg_session, dataset_release_id, image_audit_run_id, **overrides):
    defaults = dict(
        dataset_release_id=dataset_release_id,
        image_audit_run_id=image_audit_run_id,
        status="completed",
        is_completed=True,
        config={"histogram_bins": 16},
        total_items=1,
        processed_items=1,
        failed_items=0,
        total_feature_vectors=2,
        petri_feature_count=1,
        micro_feature_count=1,
        summary={"error_count": 0, "contains_model_metrics": False, "contains_taxonomy": False},
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    extraction_run = ImageFeatureExtractionRunModel(**defaults)
    pg_session.add(extraction_run)
    pg_session.flush()
    return extraction_run


def _create_split_item(pg_session, release_id, item, split=DatasetSplit.TEST) -> DatasetSplitItemModel:
    split_item = DatasetSplitItemModel(
        dataset_release_id=release_id,
        dataset_item_id=item.id,
        sample_id=item.sample_id,
        split=split,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
    )
    pg_session.add(split_item)
    pg_session.flush()
    return split_item


def _create_extraction_run_with_item(pg_session, sample_code):
    item = _create_dataset_item(pg_session, sample_code=sample_code)
    release = _create_release(pg_session, item.dataset_snapshot_id)
    audit_run = _create_audit_run(pg_session, release.id)
    extraction_run = _create_extraction_run(pg_session, release.id, audit_run.id)
    split_item = _create_split_item(pg_session, release.id, item)
    return item, release, extraction_run, split_item


def test_alembic_created_image_feature_extraction_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('image_feature_extraction_runs', 'image_feature_vectors')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["image_feature_extraction_runs", "image_feature_vectors"]


def test_image_feature_extraction_run_status_check_constraint_rejects_unknown_value(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-FEATRUN-BADSTATUS")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    audit_run = _create_audit_run(pg_session, release.id)

    with pytest.raises(IntegrityError):
        _create_extraction_run(pg_session, release.id, audit_run.id, status="not_a_real_status")


def test_image_feature_vector_modality_check_constraint_rejects_unknown_value(pg_session):
    item, release, extraction_run, split_item = _create_extraction_run_with_item(
        pg_session, "S-PG-FEATVEC-BADMODALITY"
    )

    vector = ImageFeatureVectorModel(
        feature_extraction_run_id=extraction_run.id,
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        dataset_split_item_id=split_item.id,
        split="test",
        modality="not_a_real_modality",
        image_path="petri.jpg",
        features={},
        preprocessing={},
        extraction_version="v1",
    )
    pg_session.add(vector)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_image_feature_vector_split_check_constraint_rejects_unknown_value(pg_session):
    item, release, extraction_run, split_item = _create_extraction_run_with_item(pg_session, "S-PG-FEATVEC-BADSPLIT")

    vector = ImageFeatureVectorModel(
        feature_extraction_run_id=extraction_run.id,
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        dataset_split_item_id=split_item.id,
        split="not_a_real_split",
        modality="petri",
        image_path="petri.jpg",
        features={},
        preprocessing={},
        extraction_version="v1",
    )
    pg_session.add(vector)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_image_feature_vector_unique_constraint_per_run_split_item_and_modality(pg_session):
    item, release, extraction_run, split_item = _create_extraction_run_with_item(pg_session, "S-PG-FEATVEC-UNIQUE")

    first = ImageFeatureVectorModel(
        feature_extraction_run_id=extraction_run.id,
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        dataset_split_item_id=split_item.id,
        split="test",
        modality="petri",
        image_path="petri.jpg",
        features={},
        preprocessing={},
        extraction_version="v1",
    )
    duplicate = ImageFeatureVectorModel(
        feature_extraction_run_id=extraction_run.id,
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        dataset_split_item_id=split_item.id,
        split="test",
        modality="petri",
        image_path="petri-2.jpg",
        features={},
        preprocessing={},
        extraction_version="v1",
    )
    pg_session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_image_feature_extraction_run_json_columns_round_trip_as_jsonb(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-FEATRUN-JSON")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    audit_run = _create_audit_run(pg_session, release.id)
    extraction_run = _create_extraction_run(pg_session, release.id, audit_run.id)
    pg_session.refresh(extraction_run)

    assert extraction_run.config["histogram_bins"] == 16
    assert extraction_run.summary["contains_taxonomy"] is False

    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'image_feature_extraction_runs' AND column_name = 'summary'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_image_feature_vector_features_round_trips_as_jsonb(pg_session):
    item, release, extraction_run, split_item = _create_extraction_run_with_item(pg_session, "S-PG-FEATVEC-JSON")

    vector = ImageFeatureVectorModel(
        feature_extraction_run_id=extraction_run.id,
        dataset_release_id=release.id,
        dataset_item_id=item.id,
        dataset_split_item_id=split_item.id,
        split="test",
        modality="petri",
        image_path="petri.jpg",
        features={"geometry": {"width": 100, "height": 100}},
        preprocessing={"convert_to_rgb": True},
        extraction_version="v1",
    )
    pg_session.add(vector)
    pg_session.flush()
    pg_session.refresh(vector)

    assert vector.features["geometry"]["width"] == 100

    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'image_feature_vectors' AND column_name = 'features'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_image_feature_extraction_run_foreign_keys_are_enforced(pg_session):
    extraction_run = ImageFeatureExtractionRunModel(
        dataset_release_id=uuid.uuid4(),
        image_audit_run_id=uuid.uuid4(),
        status="completed",
        is_completed=True,
        config={},
        total_items=0,
        processed_items=0,
        failed_items=0,
        total_feature_vectors=0,
        petri_feature_count=0,
        micro_feature_count=0,
        summary={},
        started_at=datetime.now(timezone.utc),
    )
    pg_session.add(extraction_run)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_image_feature_vector_foreign_keys_are_enforced(pg_session):
    item, release, extraction_run, split_item = _create_extraction_run_with_item(pg_session, "S-PG-FEATVEC-FK")

    vector = ImageFeatureVectorModel(
        feature_extraction_run_id=extraction_run.id,
        dataset_release_id=release.id,
        dataset_item_id=uuid.uuid4(),
        dataset_split_item_id=split_item.id,
        split="test",
        modality="petri",
        image_path="petri.jpg",
        features={},
        preprocessing={},
        extraction_version="v1",
    )
    pg_session.add(vector)

    with pytest.raises(IntegrityError):
        pg_session.flush()
