"""Use case: get the preliminary result for an AnalysisRun, enriched with
human review status (Fase 42).

Returns the Prediction alongside a summary of the current human review state so
callers can see whether a review has been submitted without fetching the full
final-result endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.application.exceptions import (
    AnalysisRunNotFoundError,
    PredictionNotFoundError,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.services.final_analysis_resolver import (
    FINAL_STATUS_PENDING,
    resolve_final_label,
)
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


@dataclass(frozen=True, slots=True)
class PreliminaryResultWithReviewDTO:
    """Prediction plus current human review status, for the preliminary-result endpoint."""

    analysis_run_id: UUID
    prediction_id: UUID
    predicted_label: PredictedLabel
    confidence_score: Optional[float]
    class_probabilities: Optional[dict]
    requires_human_review: bool
    technical_observation: Optional[str]
    explanation: Optional[str]
    feature_summary: Optional[dict]
    quality_summary: Optional[dict]
    decision_trace: Optional[list]
    warnings: Optional[list]
    # review status (all optional — None when no review yet)
    human_review_status: str
    human_review_completed: bool
    latest_human_review_id: Optional[UUID]
    latest_human_review_decision: Optional[ReviewDecision]
    final_label: Optional[PredictedLabel]
    reviewed_at: Optional[datetime]


class GetPreliminaryResultWithReviewUseCase:
    """Return a Prediction enriched with current human review status.

    Raises:
        AnalysisRunNotFoundError: if the AnalysisRun does not exist.
        PredictionNotFoundError: if the AnalysisRun has no Prediction yet.
    """

    def __init__(
        self,
        analysis_run_repository: AnalysisRunRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
        human_review_repository: HumanReviewRepositoryPort,
    ) -> None:
        self._analysis_run_repository = analysis_run_repository
        self._prediction_repository = prediction_repository
        self._human_review_repository = human_review_repository

    def execute(self, analysis_run_id: UUID) -> PreliminaryResultWithReviewDTO:
        analysis_run = self._analysis_run_repository.get_by_id(analysis_run_id)
        if analysis_run is None:
            raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run_id}' does not exist")

        prediction = self._prediction_repository.get_by_analysis_run_id(analysis_run_id)
        if prediction is None:
            raise PredictionNotFoundError(
                f"prediction for analysis_run '{analysis_run_id}' does not exist"
            )

        review = self._human_review_repository.get_final_by_analysis_run_id(analysis_run_id)
        resolution = resolve_final_label(prediction, review)

        return PreliminaryResultWithReviewDTO(
            analysis_run_id=analysis_run.id,
            prediction_id=prediction.id,
            predicted_label=prediction.predicted_label,
            confidence_score=prediction.confidence_score,
            class_probabilities=prediction.class_probabilities,
            requires_human_review=not resolution.human_review_completed,
            technical_observation=prediction.technical_observation,
            explanation=prediction.explanation,
            feature_summary=prediction.feature_summary,
            quality_summary=prediction.quality_summary,
            decision_trace=prediction.decision_trace,
            warnings=prediction.warnings,
            human_review_status=resolution.status,
            human_review_completed=resolution.human_review_completed,
            latest_human_review_id=review.id if review is not None else None,
            latest_human_review_decision=review.review_decision if review is not None else None,
            final_label=resolution.final_label,
            reviewed_at=review.created_at if review is not None else None,
        )
