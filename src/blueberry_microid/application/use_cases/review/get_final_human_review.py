from uuid import UUID

from blueberry_microid.application.dto.human_review_dto import HumanReviewDTO
from blueberry_microid.application.exceptions import AnalysisRunNotFoundError, HumanReviewNotFoundError
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort


class GetFinalHumanReviewUseCase:
    """Return the current expert decision for an AnalysisRun."""

    def __init__(
        self,
        analysis_run_repository: AnalysisRunRepositoryPort,
        human_review_repository: HumanReviewRepositoryPort,
    ) -> None:
        self._analysis_run_repository = analysis_run_repository
        self._human_review_repository = human_review_repository

    def execute(self, analysis_run_id: UUID) -> HumanReviewDTO:
        analysis_run = self._analysis_run_repository.get_by_id(analysis_run_id)
        if analysis_run is None:
            raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run_id}' does not exist")

        review = self._human_review_repository.get_final_by_analysis_run_id(analysis_run_id)
        if review is None:
            raise HumanReviewNotFoundError(f"final human review for analysis_run '{analysis_run_id}' does not exist")
        return HumanReviewDTO.from_entity(review)
