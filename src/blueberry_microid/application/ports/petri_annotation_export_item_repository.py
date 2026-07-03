from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.petri_annotation_export_item import PetriAnnotationExportItem


class PetriAnnotationExportItemRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, items: list[PetriAnnotationExportItem]) -> list[PetriAnnotationExportItem]:
        raise NotImplementedError

    @abstractmethod
    def list_by_export_run_id(self, export_run_id: UUID) -> list[PetriAnnotationExportItem]:
        raise NotImplementedError
