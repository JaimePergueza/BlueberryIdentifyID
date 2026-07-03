from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.training_run import TrainingRun


class TrainingRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, training_run: TrainingRun) -> TrainingRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, training_run_id: UUID) -> Optional[TrainingRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[TrainingRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_preflight_run_id(self, preflight_run_id: UUID) -> list[TrainingRun]:
        raise NotImplementedError
