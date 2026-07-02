from uuid import UUID

from blueberry_microid.application.dto.analysis_run_dto import AnalysisRunDTO
from blueberry_microid.application.exceptions import AnalysisRunNotFoundError
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort


class GetAnalysisRunUseCase:
    """Reads a single AnalysisRun by its UUID.

    Returns the workflow state (`pending`, `processing`, ...) only — this
    system does not run inference yet, so there is no Prediction to read.
    """

    def __init__(self, analysis_run_repository: AnalysisRunRepositoryPort) -> None:
        self._analysis_run_repository = analysis_run_repository

    def execute(self, analysis_run_id: UUID) -> AnalysisRunDTO:
        analysis_run = self._analysis_run_repository.get_by_id(analysis_run_id)
        if analysis_run is None:
            raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run_id}' does not exist")
        return AnalysisRunDTO.from_entity(analysis_run)
