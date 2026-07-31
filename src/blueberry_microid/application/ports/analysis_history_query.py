"""Read port for history screens and consolidated AnalysisRun traceability."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.analysis_history_dto import (
    AnalysisHistoryFilters,
    AnalysisHistoryPageDTO,
    AnalysisRunDetailDTO,
)


class AnalysisHistoryQueryPort(ABC):
    """Optimized read model independent from ORM and write repositories."""

    @abstractmethod
    def list_page(self, filters: AnalysisHistoryFilters) -> AnalysisHistoryPageDTO:
        raise NotImplementedError

    @abstractmethod
    def get_detail(self, analysis_run_id: UUID) -> Optional[AnalysisRunDetailDTO]:
        raise NotImplementedError
