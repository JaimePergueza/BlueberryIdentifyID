"""Constraint-level checks against a REAL PostgreSQL database.

These prove the *database* enforces the invariants — not just the domain
entities or Pydantic. Each test builds a row that violates a constraint via
the ORM models directly (bypassing domain-entity validation on purpose) and
asserts PostgreSQL rejects it with an IntegrityError.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.models import HumanReviewModel, PredictionModel
from tests.integration.postgres._factories import create_analysis_run

pytestmark = pytest.mark.postgres


def test_partial_unique_index_allows_only_one_final_review_per_run(pg_session):
    run = create_analysis_run(pg_session, sample_code="S-PG-FINAL")

    first_final = HumanReviewModel(
        analysis_run_id=run.id,
        reviewer_name="alice",
        review_decision=ReviewDecision.CONFIRMED,
        is_final=True,
    )
    pg_session.add(first_final)
    pg_session.commit()

    # A second final review for the same run, WITHOUT demoting the first,
    # must be rejected by the partial unique index.
    second_final = HumanReviewModel(
        analysis_run_id=run.id,
        reviewer_name="bob",
        review_decision=ReviewDecision.CONFIRMED,
        is_final=True,
    )
    pg_session.add(second_final)
    with pytest.raises(IntegrityError):
        pg_session.commit()


def test_partial_unique_index_permits_multiple_non_final_reviews(pg_session):
    run = create_analysis_run(pg_session, sample_code="S-PG-HISTORY")

    pg_session.add(
        HumanReviewModel(
            analysis_run_id=run.id,
            reviewer_name="alice",
            review_decision=ReviewDecision.CONFIRMED,
            is_final=False,
        )
    )
    pg_session.add(
        HumanReviewModel(
            analysis_run_id=run.id,
            reviewer_name="bob",
            review_decision=ReviewDecision.CONFIRMED,
            is_final=False,
        )
    )
    # Two historical (non-final) reviews coexisting is allowed — the index
    # only constrains is_final = true rows.
    pg_session.commit()


def test_confidence_score_check_constraint_rejects_out_of_range(pg_session):
    run = create_analysis_run(pg_session, sample_code="S-PG-CONF")

    prediction = PredictionModel(
        analysis_run_id=run.id,
        predicted_label=PredictedLabel.NO_EVIDENT_GROWTH,
        confidence_score=1.5,  # out of [0, 1]
    )
    pg_session.add(prediction)
    with pytest.raises(IntegrityError):
        pg_session.commit()


def test_confidence_score_check_constraint_allows_null_and_in_range(pg_session):
    run_a = create_analysis_run(pg_session, sample_code="S-PG-CONF-NULL")
    run_b = create_analysis_run(pg_session, sample_code="S-PG-CONF-OK")

    pg_session.add(
        PredictionModel(
            analysis_run_id=run_a.id,
            predicted_label=PredictedLabel.NO_EVIDENT_GROWTH,
            confidence_score=None,
        )
    )
    pg_session.add(
        PredictionModel(
            analysis_run_id=run_b.id,
            predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
            confidence_score=0.5,
        )
    )
    pg_session.commit()  # neither should raise


def test_corrected_label_required_when_decision_is_corrected(pg_session):
    run = create_analysis_run(pg_session, sample_code="S-PG-CORR")

    review = HumanReviewModel(
        analysis_run_id=run.id,
        reviewer_name="alice",
        review_decision=ReviewDecision.CORRECTED,
        corrected_label=None,  # violates the CHECK constraint
    )
    pg_session.add(review)
    with pytest.raises(IntegrityError):
        pg_session.commit()


def test_corrected_label_accepted_when_provided_for_corrected_decision(pg_session):
    run = create_analysis_run(pg_session, sample_code="S-PG-CORR-OK")

    review = HumanReviewModel(
        analysis_run_id=run.id,
        reviewer_name="alice",
        review_decision=ReviewDecision.CORRECTED,
        corrected_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH,
    )
    pg_session.add(review)
    pg_session.commit()  # should not raise
