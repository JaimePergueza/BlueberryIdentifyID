from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


@dataclass(frozen=True, slots=True)
class SubmitHumanReviewRequest:
    """Input for submitting an expert review of one AnalysisRun."""

    analysis_run_id: UUID
    reviewer_name: str
    review_decision: ReviewDecision
    corrected_label: Optional[PredictedLabel] = None
    comments: Optional[str] = None
    is_final: bool = True


@dataclass(frozen=True, slots=True)
class HumanReviewDTO:
    """Output representation of a HumanReview, decoupled from the ORM."""

    id: UUID
    analysis_run_id: UUID
    reviewer_name: str
    review_decision: ReviewDecision
    corrected_label: Optional[PredictedLabel]
    comments: Optional[str]
    is_final: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, review: HumanReview) -> "HumanReviewDTO":
        return cls(
            id=review.id,
            analysis_run_id=review.analysis_run_id,
            reviewer_name=review.reviewer_name,
            review_decision=review.review_decision,
            corrected_label=review.corrected_label,
            comments=review.comments,
            is_final=review.is_final,
            created_at=review.created_at,
        )
