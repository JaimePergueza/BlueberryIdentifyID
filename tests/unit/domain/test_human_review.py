from uuid import uuid4

import pytest

from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.exceptions.errors import MissingCorrectedLabelError


def test_human_review_corrected_requires_corrected_label():
    with pytest.raises(MissingCorrectedLabelError):
        HumanReview(
            analysis_run_id=uuid4(),
            reviewer_name="Dra. Lopez",
            review_decision=ReviewDecision.CORRECTED,
        )


def test_human_review_corrected_with_label_is_valid():
    review = HumanReview(
        analysis_run_id=uuid4(),
        reviewer_name="Dra. Lopez",
        review_decision=ReviewDecision.CORRECTED,
        corrected_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH,
    )

    assert review.corrected_label == PredictedLabel.PROBABLE_FUNGAL_GROWTH


def test_human_review_confirmed_does_not_require_corrected_label():
    review = HumanReview(
        analysis_run_id=uuid4(),
        reviewer_name="Dra. Lopez",
        review_decision=ReviewDecision.CONFIRMED,
    )

    assert review.corrected_label is None


def test_human_review_defaults_to_final():
    review = HumanReview(
        analysis_run_id=uuid4(),
        reviewer_name="Dra. Lopez",
        review_decision=ReviewDecision.CONFIRMED,
    )

    assert review.is_final is True


def test_human_review_can_be_created_as_historical_non_final():
    review = HumanReview(
        analysis_run_id=uuid4(),
        reviewer_name="Dra. Lopez",
        review_decision=ReviewDecision.MARKED_INCONCLUSIVE,
        is_final=False,
    )

    assert review.is_final is False
