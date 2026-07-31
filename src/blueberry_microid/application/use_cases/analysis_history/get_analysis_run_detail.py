"""Use case for the consolidated detail of an AnalysisRun."""

from uuid import UUID

from blueberry_microid.application.dto.analysis_history_dto import AnalysisRunDetailDTO
from blueberry_microid.application.exceptions import AnalysisRunNotFoundError
from blueberry_microid.application.ports.analysis_history_query import AnalysisHistoryQueryPort


class GetAnalysisRunDetailUseCase:
    def __init__(self, query: AnalysisHistoryQueryPort) -> None:
        self._query = query

    def execute(self, analysis_run_id: UUID) -> AnalysisRunDetailDTO:
        detail = self._query.get_detail(analysis_run_id)
        if detail is None:
            raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run_id}' does not exist")
        return detail
