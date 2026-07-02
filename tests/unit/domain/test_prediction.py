from uuid import uuid4

import pytest

from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.exceptions.errors import InvalidConfidenceScoreError


def test_prediction_accepts_confidence_score_within_range():
    prediction = Prediction(
        analysis_run_id=uuid4(),
        predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
        confidence_score=0.75,
    )

    assert prediction.confidence_score == 0.75


@pytest.mark.parametrize("out_of_range_score", [-0.01, 1.01, 5.0, -3.0])
def test_prediction_rejects_confidence_score_out_of_range(out_of_range_score):
    with pytest.raises(InvalidConfidenceScoreError):
        Prediction(
            analysis_run_id=uuid4(),
            predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
            confidence_score=out_of_range_score,
        )


def test_inconclusive_prediction_always_requires_human_review():
    prediction = Prediction(
        analysis_run_id=uuid4(),
        predicted_label=PredictedLabel.INCONCLUSIVE,
        requires_human_review=False,
    )

    assert prediction.requires_human_review is True
