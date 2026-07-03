from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.petri_annotation_export_run import PetriAnnotationExportRun


class PetriAnnotationExportRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, export_run: PetriAnnotationExportRun) -> PetriAnnotationExportRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, export_run_id: UUID) -> Optional[PetriAnnotationExportRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[PetriAnnotationExportRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriAnnotationExportRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_petri_segmentation_run_id(self, petri_segmentation_run_id: UUID) -> list[PetriAnnotationExportRun]:
        raise NotImplementedError
