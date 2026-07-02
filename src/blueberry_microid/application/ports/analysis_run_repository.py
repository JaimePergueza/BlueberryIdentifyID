from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.analysis_run import AnalysisRun


class AnalysisRunRepositoryPort(ABC):
    """Persistence contract for AnalysisRun, independent of any ORM."""

    @abstractmethod
    def add(self, analysis_run: AnalysisRun) -> AnalysisRun:
        raise NotImplementedError

    @abstractmethod
    def update(self, analysis_run: AnalysisRun) -> AnalysisRun:
        """Persist a status transition (and started_at/completed_at/error_message).

        Raises AnalysisRunNotFoundError if the row no longer exists. This is
        an unconditional overwrite — safe for the `processing -> final state`
        step because, by the time a caller reaches it, `claim_for_processing`
        has already guaranteed it is the only writer for this AnalysisRun.
        Never use this method to perform the `pending -> processing`
        transition itself; that must go through `claim_for_processing`.
        """
        raise NotImplementedError

    @abstractmethod
    def claim_for_processing(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        """Atomically transition `pending -> processing`, or fail silently.

        This is the concurrency-safety mechanism for
        `ProcessAnalysisRunUseCase`: two callers racing to process the same
        AnalysisRun cannot both succeed, because the underlying update is a
        single conditional write (`UPDATE ... WHERE id = ? AND status =
        'pending'`) rather than a read-modify-write done in Python. Returns
        the freshly-claimed AnalysisRun (now `processing`) if this call won
        the race, or `None` if the row was not `pending` (already claimed by
        another call, or already in a final state) — callers must not treat
        `None` as "not found"; existence should already have been checked via
        `get_by_id` beforehand.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_sample_id(self, sample_id: UUID) -> list[AnalysisRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[AnalysisRun]:
        raise NotImplementedError
