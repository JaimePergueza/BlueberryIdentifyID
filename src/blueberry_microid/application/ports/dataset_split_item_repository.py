from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.enums.dataset_split import DatasetSplit


class DatasetSplitItemRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, dataset_split_items: list[DatasetSplitItem]) -> list[DatasetSplitItem]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DatasetSplitItem]:
        raise NotImplementedError

    @abstractmethod
    def list_by_split(self, dataset_release_id: UUID, split: DatasetSplit) -> list[DatasetSplitItem]:
        raise NotImplementedError
