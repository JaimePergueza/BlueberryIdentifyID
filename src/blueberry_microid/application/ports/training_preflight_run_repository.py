from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.training_preflight_run import TrainingPreflightRun


class TrainingPreflightRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, preflight_run: TrainingPreflightRun) -> TrainingPreflightRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, preflight_run_id: UUID) -> Optional[TrainingPreflightRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingPreflightRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[TrainingPreflightRun]:
        raise NotImplementedError
