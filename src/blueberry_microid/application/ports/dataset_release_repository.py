from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.dataset_release import DatasetRelease


class DatasetReleaseRepositoryPort(ABC):
    @abstractmethod
    def add(self, dataset_release: DatasetRelease) -> DatasetRelease:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, dataset_release_id: UUID) -> Optional[DatasetRelease]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> list[DatasetRelease]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DatasetRelease]:
        raise NotImplementedError
