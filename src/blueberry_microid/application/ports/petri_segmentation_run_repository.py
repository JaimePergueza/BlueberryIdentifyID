from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun


class PetriSegmentationRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, segmentation_run: PetriSegmentationRun) -> PetriSegmentationRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, segmentation_run_id: UUID) -> Optional[PetriSegmentationRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[PetriSegmentationRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriSegmentationRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_image_audit_run_id(self, image_audit_run_id: UUID) -> list[PetriSegmentationRun]:
        raise NotImplementedError
