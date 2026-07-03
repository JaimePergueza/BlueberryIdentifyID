from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.enums.dataset_split import DatasetSplit


class PetriSegmentationRegionRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, regions: list[PetriSegmentationRegion]) -> list[PetriSegmentationRegion]:
        raise NotImplementedError

    @abstractmethod
    def list_by_segmentation_run_id(self, segmentation_run_id: UUID) -> list[PetriSegmentationRegion]:
        raise NotImplementedError

    @abstractmethod
    def list_by_segmentation_run_id_and_split(
        self, segmentation_run_id: UUID, split: DatasetSplit
    ) -> list[PetriSegmentationRegion]:
        raise NotImplementedError
