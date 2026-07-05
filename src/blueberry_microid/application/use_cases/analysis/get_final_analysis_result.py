"""Use case: get the final analysis result for an AnalysisRun (Fase 42).

Combines the automatic Prediction with the current expert HumanReview (if any)
and resolves the final label.  The Prediction is never modified.
"""

from __future__ import annotations

from uuid import UUID

from blueberry_microid.application.dto.final_analysis_result_dto import (
    FinalAnalysisResultDTO,
    _FINAL_RESULT_DISCLAIMER,
)
from blueberry_microid.application.exceptions import (
    AnalysisRunNotFoundError,
    PredictionNotFoundError,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.services.final_analysis_resolver import resolve_final_label


class GetFinalAnalysisResultUseCase:
    """Return the combined Prediction + HumanReview view for an AnalysisRun.

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

    def execute(self, analysis_run_id: UUID) -> FinalAnalysisResultDTO:
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

        return FinalAnalysisResultDTO(
            analysis_run_id=analysis_run.id,
            sample_id=analysis_run.sample_id,
            prediction_id=prediction.id,
            preliminary_label=prediction.predicted_label,
            confidence_score=prediction.confidence_score,
            explanation=prediction.explanation,
            feature_summary=prediction.feature_summary,
            quality_summary=prediction.quality_summary,
            decision_trace=prediction.decision_trace,
            automatic_warnings=prediction.warnings,
            human_review_id=review.id if review is not None else None,
            human_review_decision=review.review_decision if review is not None else None,
            corrected_label=review.corrected_label if review is not None else None,
            reviewer_name=review.reviewer_name if review is not None else None,
            human_comments=review.comments if review is not None else None,
            reviewed_at=review.created_at if review is not None else None,
            final_label=resolution.final_label,
            status=resolution.status,
            human_review_completed=resolution.human_review_completed,
            requires_human_review=not resolution.human_review_completed,
            disclaimer=_FINAL_RESULT_DISCLAIMER,
        )
