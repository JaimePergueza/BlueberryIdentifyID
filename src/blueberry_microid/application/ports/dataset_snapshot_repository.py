from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot


class DatasetSnapshotRepositoryPort(ABC):
    @abstractmethod
    def add(self, dataset_snapshot: DatasetSnapshot) -> DatasetSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, dataset_snapshot_id: UUID) -> Optional[DatasetSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DatasetSnapshot]:
        raise NotImplementedError

