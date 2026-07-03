from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.training_run_comparison_entry import TrainingRunComparisonEntry


class TrainingRunComparisonEntryRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, entries: list[TrainingRunComparisonEntry]) -> list[TrainingRunComparisonEntry]:
        raise NotImplementedError

    @abstractmethod
    def list_by_comparison_id(self, comparison_id: UUID) -> list[TrainingRunComparisonEntry]:
        raise NotImplementedError
