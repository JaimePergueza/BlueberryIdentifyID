from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.training_run_comparison import TrainingRunComparison


class TrainingRunComparisonRepositoryPort(ABC):
    @abstractmethod
    def add(self, comparison: TrainingRunComparison) -> TrainingRunComparison:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, comparison_id: UUID) -> Optional[TrainingRunComparison]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[TrainingRunComparison]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingRunComparison]:
        raise NotImplementedError
