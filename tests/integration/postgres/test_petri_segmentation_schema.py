import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.db.models import (
    DatasetSplitItemModel,
    PetriSegmentationRegionModel,
    PetriSegmentationRunModel,
)
from tests.integration.postgres.test_dataset_release_schema import _create_dataset_item, _create_release

pytestmark = pytest.mark.postgres


def _create_segmentation_run_with_split_item(pg_session):
    item = _create_dataset_item(pg_session, sample_code=f"S-PG-PETRI-SEG-{uuid.uuid4()}")
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
    run = PetriSegmentationRunModel(
        dataset_release_id=release.id,
        status="completed",
        is_completed=True,
        config={"algorithm": "classical_threshold"},
        total_items=1,
        processed_petri_images=1,
        failed_petri_images=0,
        total_regions_detected=1,
        mean_regions_per_image=1.0,
        summary={"contains_deep_learning": False},
        started_at=datetime.now(timezone.utc),
    )
    pg_session.add(run)
    pg_session.flush()
    return run, split_item, item


def test_alembic_created_petri_segmentation_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('petri_segmentation_runs', 'petri_segmentation_regions')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["petri_segmentation_regions", "petri_segmentation_runs"]


def test_petri_segmentation_status_check_constraint_rejects_unknown_value(pg_session):
    item = _create_dataset_item(pg_session, sample_code=f"S-PG-PETRI-SEG-BAD-{uuid.uuid4()}")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    run = PetriSegmentationRunModel(
        dataset_release_id=release.id,
        status="diagnosed",
        is_completed=True,
        config={},
        total_items=1,
        processed_petri_images=1,
        failed_petri_images=0,
        total_regions_detected=0,
        summary={},
        started_at=datetime.now(timezone.utc),
    )
    pg_session.add(run)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_petri_segmentation_unique_constraint_per_run_split_item_and_region_index(pg_session):
    run, split_item, item = _create_segmentation_run_with_split_item(pg_session)
    first = _region(run, split_item, item, region_index=0)
    duplicate = _region(run, split_item, item, region_index=0)
    pg_session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_petri_segmentation_json_columns_round_trip_as_jsonb(pg_session):
    run, split_item, item = _create_segmentation_run_with_split_item(pg_session)
    region = _region(run, split_item, item, region_features={"candidate_region": True})
    pg_session.add(region)
    pg_session.flush()
    pg_session.refresh(run)
    pg_session.refresh(region)

    assert run.summary["contains_deep_learning"] is False
    assert region.region_features["candidate_region"] is True
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'petri_segmentation_regions' AND column_name = 'region_features'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_petri_segmentation_foreign_keys_are_enforced(pg_session):
    run, split_item, item = _create_segmentation_run_with_split_item(pg_session)
    region = _region(run, split_item, item)
    region.segmentation_run_id = uuid.uuid4()
    pg_session.add(region)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def _region(run, split_item, item, *, region_index=0, region_features=None):
    return PetriSegmentationRegionModel(
        segmentation_run_id=run.id,
        dataset_release_id=run.dataset_release_id,
        dataset_item_id=item.id,
        dataset_split_item_id=split_item.id,
        split="train",
        petri_image_path="/pg/petri.png",
        region_index=region_index,
        area_px=100.0,
        perimeter_px=40.0,
        centroid_x=20.0,
        centroid_y=20.0,
        bbox_x=10,
        bbox_y=10,
        bbox_width=20,
        bbox_height=20,
        circularity=0.8,
        solidity=0.9,
        mean_intensity=42.0,
        region_features=region_features or {},
    )
