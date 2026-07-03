import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import PetriRegionReviewModel
from tests.integration.postgres.test_petri_segmentation_schema import _create_segmentation_run_with_split_item, _region

pytestmark = pytest.mark.postgres


def _create_region(pg_session):
    run, split_item, item = _create_segmentation_run_with_split_item(pg_session)
    region = _region(run, split_item, item)
    pg_session.add(region)
    pg_session.flush()
    return run, region, item, split_item


def _review(run, region, item, split_item, *, decision="candidate_valid", is_final=True, **kwargs):
    return PetriRegionReviewModel(
        petri_segmentation_region_id=region.id,
        petri_segmentation_run_id=run.id,
        dataset_release_id=run.dataset_release_id,
        dataset_item_id=item.id,
        dataset_split_item_id=split_item.id,
        decision=decision,
        is_final=is_final,
        **kwargs,
    )


def test_alembic_created_petri_region_reviews_table(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'petri_region_reviews'
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["petri_region_reviews"]


def test_decision_check_constraint_rejects_unknown_value(pg_session):
    run, region, item, split_item = _create_region(pg_session)
    review = _review(run, region, item, split_item, decision="not_a_real_decision")
    pg_session.add(review)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_confidence_score_check_constraint_rejects_out_of_range_value(pg_session):
    run, region, item, split_item = _create_region(pg_session)
    review = _review(run, region, item, split_item, confidence_score=1.5)
    pg_session.add(review)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_corrected_bbox_width_check_constraint_rejects_non_positive_value(pg_session):
    run, region, item, split_item = _create_region(pg_session)
    review = _review(run, region, item, split_item, corrected_bbox_width=0)
    pg_session.add(review)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_corrected_bbox_height_check_constraint_rejects_non_positive_value(pg_session):
    run, region, item, split_item = _create_region(pg_session)
    review = _review(run, region, item, split_item, corrected_bbox_height=-1)
    pg_session.add(review)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_partial_unique_index_allows_only_one_final_review_per_region(pg_session):
    run, region, item, split_item = _create_region(pg_session)
    first = _review(run, region, item, split_item, is_final=True)
    pg_session.add(first)
    pg_session.flush()

    second = _review(run, region, item, split_item, decision="candidate_false_positive", is_final=True)
    pg_session.add(second)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_partial_unique_index_allows_multiple_non_final_reviews_per_region(pg_session):
    run, region, item, split_item = _create_region(pg_session)
    first = _review(run, region, item, split_item, is_final=False)
    second = _review(run, region, item, split_item, decision="candidate_uncertain", is_final=False)
    pg_session.add_all([first, second])

    pg_session.flush()  # should not raise


def test_foreign_keys_are_enforced(pg_session):
    run, region, item, split_item = _create_region(pg_session)
    review = _review(run, region, item, split_item)
    review.petri_segmentation_region_id = uuid.uuid4()
    pg_session.add(review)

    with pytest.raises(IntegrityError):
        pg_session.flush()
