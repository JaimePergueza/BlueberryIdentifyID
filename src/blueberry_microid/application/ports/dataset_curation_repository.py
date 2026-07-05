from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.dataset_curation_item import DatasetCurationItem
from blueberry_microid.domain.entities.dataset_curation_run import DatasetCurationRun
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus


class DatasetCurationRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, curation_run: DatasetCurationRun) -> DatasetCurationRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, curation_run_id: UUID) -> Optional[DatasetCurationRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DatasetCurationRun]:
        raise NotImplementedError

    @abstractmethod
    def set_created_snapshot_id(self, curation_run_id: UUID, dataset_snapshot_id: UUID) -> DatasetCurationRun:
        raise NotImplementedError


class DatasetCurationItemRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, curation_items: list[DatasetCurationItem]) -> list[DatasetCurationItem]:
        raise NotImplementedError

    @abstractmethod
    def list_by_curation_run_id(
        self,
        curation_run_id: UUID,
        *,
        status: Optional[DatasetCurationStatus] = None,
    ) -> list[DatasetCurationItem]:
        raise NotImplementedError

    @abstractmethod
    def count_by_curation_run_id(self, curation_run_id: UUID) -> int:
        raise NotImplementedError
