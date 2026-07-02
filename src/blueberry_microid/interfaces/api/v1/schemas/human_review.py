from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


class HumanReviewCreate(BaseModel):
    """Payload an expert submits to review an AnalysisRun's Prediction."""

    model_config = ConfigDict(extra="forbid")

    reviewer_name: str = Field(min_length=1, max_length=255)
    review_decision: ReviewDecision
    corrected_label: Optional[PredictedLabel] = None
    comments: Optional[str] = None
    is_final: bool = True

    @model_validator(mode="after")
    def validate_review_decision_details(self) -> "HumanReviewCreate":
        if self.review_decision == ReviewDecision.CORRECTED and self.corrected_label is None:
            raise ValueError("corrected_label is required when review_decision is 'corrected'")
        if (
            self.review_decision == ReviewDecision.MARKED_INCONCLUSIVE
            and self.corrected_label is not None
            and self.corrected_label != PredictedLabel.INCONCLUSIVE
        ):
            raise ValueError("corrected_label must be 'inconclusive' when review_decision is 'marked_inconclusive'")
        return self


class HumanReviewRead(BaseModel):
    """Representation of a HumanReview returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_run_id: UUID
    reviewer_name: str
    review_decision: ReviewDecision
    corrected_label: Optional[PredictedLabel]
    comments: Optional[str]
    is_final: bool
    created_at: datetime


class HumanReviewListResponse(BaseModel):
    """Historical HumanReview list, ordered oldest to newest."""

    reviews: list[HumanReviewRead]
