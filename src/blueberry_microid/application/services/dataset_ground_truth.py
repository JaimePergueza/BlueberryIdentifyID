from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


@dataclass(frozen=True, slots=True)
class GroundTruthDecision:
    ground_truth_label: Optional[PredictedLabel]
    included: bool
    exclusion_reason: Optional[str] = None


def derive_ground_truth_label(
    *,
    prediction: Prediction,
    final_review: HumanReview,
    include_inconclusive: bool = False,
    include_rejected: bool = False,
) -> GroundTruthDecision:
    """Derive dataset label from final HumanReview, never from Prediction alone."""

    if final_review.review_decision == ReviewDecision.CONFIRMED:
        return GroundTruthDecision(prediction.predicted_label, True)
    if final_review.review_decision == ReviewDecision.CORRECTED:
        return GroundTruthDecision(final_review.corrected_label, True)
    if final_review.review_decision == ReviewDecision.MARKED_INCONCLUSIVE:
        if include_inconclusive:
            return GroundTruthDecision(PredictedLabel.INCONCLUSIVE, True)
        return GroundTruthDecision(PredictedLabel.INCONCLUSIVE, False, "marked_inconclusive")
    if final_review.review_decision == ReviewDecision.REJECTED_INVALID_SAMPLE:
        if include_rejected:
            return GroundTruthDecision(None, False, "rejected_invalid_sample")
        return GroundTruthDecision(None, False, "rejected_invalid_sample")
    return GroundTruthDecision(None, False, "unsupported_review_decision")

