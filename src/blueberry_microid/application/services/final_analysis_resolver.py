"""Resolves the final label for an AnalysisRun from Prediction + HumanReview.

This module is pure domain logic with no I/O.  It never opens images, never
trains models, never asserts taxonomy.  The "final label" is an operational
classification (one of the five preliminary visual categories) derived from
expert review, not a microbiological identification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision

# ─── status constants ────────────────────────────────────────────────────────
FINAL_STATUS_PENDING = "pending_human_review"
FINAL_STATUS_CONFIRMED = "human_confirmed"
FINAL_STATUS_CORRECTED = "human_corrected"
FINAL_STATUS_INCONCLUSIVE = "inconclusive"
FINAL_STATUS_REJECTED = "rejected_invalid_sample"


@dataclass(frozen=True, slots=True)
class FinalLabelResolution:
    """Result of resolving the final label for an AnalysisRun.

    ``final_label`` is ``None`` when no human review exists yet or when the
    sample was rejected as invalid.  ``status`` is always one of the five
    ``FINAL_STATUS_*`` constants above.  ``human_review_completed`` is ``True``
    once any final review has been submitted (even if the sample was rejected).
    """

    final_label: Optional[PredictedLabel]
    status: str
    human_review_completed: bool


def resolve_final_label(
    prediction: Prediction,
    review: Optional[HumanReview],
) -> FinalLabelResolution:
    """Derive the final label and workflow status from a Prediction and review.

    Rules (ordered):
    - No review → ``pending_human_review``, ``final_label=None``
    - ``confirmed`` → ``human_confirmed``, ``final_label=prediction.predicted_label``
    - ``corrected`` → ``human_corrected``, ``final_label=review.corrected_label``
    - ``marked_inconclusive`` → ``inconclusive``, ``final_label=PredictedLabel.INCONCLUSIVE``
    - ``rejected_invalid_sample`` → ``rejected_invalid_sample``, ``final_label=None``

    The ``prediction`` argument is required to resolve the ``confirmed`` case.
    It is not modified.
    """
    if review is None:
        return FinalLabelResolution(
            final_label=None,
            status=FINAL_STATUS_PENDING,
            human_review_completed=False,
        )

    decision = review.review_decision

    if decision == ReviewDecision.CONFIRMED:
        return FinalLabelResolution(
            final_label=prediction.predicted_label,
            status=FINAL_STATUS_CONFIRMED,
            human_review_completed=True,
        )

    if decision == ReviewDecision.CORRECTED:
        return FinalLabelResolution(
            final_label=review.corrected_label,
            status=FINAL_STATUS_CORRECTED,
            human_review_completed=True,
        )

    if decision == ReviewDecision.MARKED_INCONCLUSIVE:
        return FinalLabelResolution(
            final_label=PredictedLabel.INCONCLUSIVE,
            status=FINAL_STATUS_INCONCLUSIVE,
            human_review_completed=True,
        )

    # ReviewDecision.REJECTED_INVALID_SAMPLE
    return FinalLabelResolution(
        final_label=None,
        status=FINAL_STATUS_REJECTED,
        human_review_completed=True,
    )
