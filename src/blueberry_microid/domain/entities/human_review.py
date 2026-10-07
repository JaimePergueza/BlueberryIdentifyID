from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.exceptions.errors import MissingCorrectedLabelError


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class HumanReview:
    """An expert's review of an AnalysisRun's Prediction.

    Never overwrites the original Prediction — both are kept for full
    traceability. A `corrected` decision must always carry a corrected_label.

    `is_final` distinguishes the review that currently stands for an
    AnalysisRun from historical ones (e.g. a first pass later superseded by
    a second opinion). At most one HumanReview per AnalysisRun should have
    `is_final=True` at any given time; this entity cannot enforce that by
    itself since the invariant spans multiple rows. It is enforced at the
    database level with a partial unique index and by
    SubmitHumanReviewUseCase, which demotes any previous final review before
    adding the new final review in one UnitOfWork.
    """

    analysis_run_id: UUID
    reviewer_name: str
    review_decision: ReviewDecision
    id: UUID = field(default_factory=uuid4)
    corrected_label: Optional[PredictedLabel] = None
    comments: Optional[str] = None
    is_final: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    reviewer_user_id: Optional[UUID] = None
    reviewed_colony_count: Optional[int] = None

    def __post_init__(self) -> None:
        if self.reviewed_colony_count is not None and (
            type(self.reviewed_colony_count) is not int
            or not 0 <= self.reviewed_colony_count <= 100000
        ):
            raise ValueError("reviewed_colony_count must be an integer between 0 and 100000")
        if (
            self.review_decision == ReviewDecision.REJECTED_INVALID_SAMPLE
            and self.reviewed_colony_count is not None
        ):
            raise ValueError("an invalid sample cannot have a confirmed colony count")
        if self.review_decision == ReviewDecision.CORRECTED and self.corrected_label is None:
            raise MissingCorrectedLabelError(
                "corrected_label is required when review_decision is 'corrected'"
            )
