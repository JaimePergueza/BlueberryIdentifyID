from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.dataset_item import DatasetItem


class DatasetItemRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, dataset_items: list[DatasetItem]) -> list[DatasetItem]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> list[DatasetItem]:
        raise NotImplementedError

    @abstractmethod
    def count_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    def label_distribution_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> dict[str, int]:
        raise NotImplementedError

