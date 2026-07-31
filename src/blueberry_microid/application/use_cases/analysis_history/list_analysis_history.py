"""Use case for paginated AnalysisRun history."""

from blueberry_microid.application.dto.analysis_history_dto import (
    AnalysisHistoryFilters,
    AnalysisHistoryPageDTO,
)
from blueberry_microid.application.ports.analysis_history_query import AnalysisHistoryQueryPort


class ListAnalysisHistoryUseCase:
    def __init__(self, query: AnalysisHistoryQueryPort) -> None:
        self._query = query

    def execute(self, filters: AnalysisHistoryFilters) -> AnalysisHistoryPageDTO:
        return self._query.list_page(filters)
