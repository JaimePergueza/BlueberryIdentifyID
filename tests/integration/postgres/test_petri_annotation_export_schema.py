import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import (
    PetriAnnotationExportItemModel,
    PetriAnnotationExportRunModel,
)
from tests.integration.postgres.test_petri_region_review_schema import _create_region, _review

pytestmark = pytest.mark.postgres


def _create_export_run_with_review(pg_session):
    run, region, item, split_item = _create_region(pg_session)
    review = _review(run, region, item, split_item)
    pg_session.add(review)
    pg_session.flush()
    export_run = PetriAnnotationExportRunModel(
        dataset_release_id=run.dataset_release_id,
        petri_segmentation_run_id=run.id,
        export_format="blueberry_manifest",
        status="completed",
        is_completed=True,
        config={"export_format": "blueberry_manifest"},
        exported_annotation_count=1,
        skipped_review_count=0,
        image_count=1,
        category_count=1,
        output_manifest={"annotations": [{"label": "candidate_region"}]},
        summary={"contains_taxonomy": False},
    )
    pg_session.add(export_run)
    pg_session.flush()
    return export_run, review, run, region, item, split_item


def _item(export_run, review, run, region, item, split_item, **kwargs):
    return PetriAnnotationExportItemModel(
        export_run_id=export_run.id,
        petri_region_review_id=review.id,
        petri_segmentation_region_id=region.id,
        dataset_release_id=run.dataset_release_id,
        dataset_item_id=item.id,
        dataset_split_item_id=split_item.id,
        split="train",
        petri_image_path="/pg/petri.png",
        export_label="candidate_region",
        bbox_x=10,
        bbox_y=10,
        bbox_width=20,
        bbox_height=20,
        bbox_source="original",
        export_payload={"label": "candidate_region"},
        **kwargs,
    )


def test_alembic_created_petri_annotation_export_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('petri_annotation_export_runs', 'petri_annotation_export_items')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["petri_annotation_export_items", "petri_annotation_export_runs"]


def test_export_format_check_constraint_rejects_unknown_value(pg_session):
    export_run, *_ = _create_export_run_with_review(pg_session)
    export_run.export_format = "tensorflow_saved_model"

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_status_check_constraint_rejects_unknown_value(pg_session):
    export_run, *_ = _create_export_run_with_review(pg_session)
    export_run.status = "training"

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_bbox_source_and_dimensions_constraints(pg_session):
    export_run, review, run, region, item, split_item = _create_export_run_with_review(pg_session)
    bad = _item(export_run, review, run, region, item, split_item, bbox_source="mask", bbox_width=0)
    pg_session.add(bad)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_unique_export_run_review_constraint(pg_session):
    export_run, review, run, region, item, split_item = _create_export_run_with_review(pg_session)
    first = _item(export_run, review, run, region, item, split_item)
    duplicate = _item(export_run, review, run, region, item, split_item)
    pg_session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_json_columns_round_trip_as_jsonb(pg_session):
    export_run, review, run, region, item, split_item = _create_export_run_with_review(pg_session)
    export_item = _item(export_run, review, run, region, item, split_item)
    pg_session.add(export_item)
    pg_session.flush()
    pg_session.refresh(export_run)
    pg_session.refresh(export_item)

    assert export_run.output_manifest["annotations"][0]["label"] == "candidate_region"
    assert export_item.export_payload["label"] == "candidate_region"
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'petri_annotation_export_runs' AND column_name = 'output_manifest'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_foreign_keys_are_enforced(pg_session):
    export_run, review, run, region, item, split_item = _create_export_run_with_review(pg_session)
    export_item = _item(export_run, review, run, region, item, split_item)
    export_item.petri_region_review_id = uuid.uuid4()
    pg_session.add(export_item)

    with pytest.raises(IntegrityError):
        pg_session.flush()
