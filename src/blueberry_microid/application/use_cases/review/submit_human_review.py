from blueberry_microid.application.dto.human_review_dto import HumanReviewDTO, SubmitHumanReviewRequest
from blueberry_microid.application.exceptions import (
    AnalysisRunNotFoundError,
    AnalysisRunNotReviewableError,
    PredictionNotFoundError,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus

_NON_REVIEWABLE_STATUSES = {AnalysisStatus.PENDING, AnalysisStatus.PROCESSING}


class SubmitHumanReviewUseCase:
    """Record an expert review without mutating the original Prediction."""

    def __init__(
        self,
        analysis_run_repository: AnalysisRunRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._analysis_run_repository = analysis_run_repository
        self._prediction_repository = prediction_repository
        self._unit_of_work = unit_of_work

    def execute(self, request: SubmitHumanReviewRequest) -> HumanReviewDTO:
        analysis_run = self._analysis_run_repository.get_by_id(request.analysis_run_id)
        if analysis_run is None:
            raise AnalysisRunNotFoundError(f"analysis_run '{request.analysis_run_id}' does not exist")

        if analysis_run.status in _NON_REVIEWABLE_STATUSES:
            raise AnalysisRunNotReviewableError(
                f"cannot review AnalysisRun '{analysis_run.id}' while status is '{analysis_run.status.value}'"
            )

        if self._prediction_repository.get_by_analysis_run_id(request.analysis_run_id) is None:
            raise PredictionNotFoundError(
                f"prediction for analysis_run '{request.analysis_run_id}' does not exist"
            )

        review = HumanReview(
            analysis_run_id=request.analysis_run_id,
            reviewer_name=request.reviewer_name,
            review_decision=request.review_decision,
            corrected_label=request.corrected_label,
            comments=request.comments,
            is_final=request.is_final,
        )

        with self._unit_of_work as uow:
            if review.is_final:
                uow.human_review_repository.unset_final_reviews_for_analysis_run(request.analysis_run_id)
            created = uow.human_review_repository.add(review)
            uow.commit()

        return HumanReviewDTO.from_entity(created)
