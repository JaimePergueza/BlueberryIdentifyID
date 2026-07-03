from uuid import UUID

from blueberry_microid.application.dto.petri_annotation_export_dto import PetriAnnotationExportItemDTO
from blueberry_microid.application.exceptions import PetriAnnotationExportRunNotFoundError
from blueberry_microid.application.ports.petri_annotation_export_item_repository import (
    PetriAnnotationExportItemRepositoryPort,
)
from blueberry_microid.application.ports.petri_annotation_export_run_repository import (
    PetriAnnotationExportRunRepositoryPort,
)


class ListPetriAnnotationExportItemsUseCase:
    def __init__(
        self,
        run_repository: PetriAnnotationExportRunRepositoryPort,
        item_repository: PetriAnnotationExportItemRepositoryPort,
    ) -> None:
        self._run_repository = run_repository
        self._item_repository = item_repository

    def execute(self, export_run_id: UUID) -> list[PetriAnnotationExportItemDTO]:
        if self._run_repository.get_by_id(export_run_id) is None:
            raise PetriAnnotationExportRunNotFoundError(
                f"petri_annotation_export_run '{export_run_id}' does not exist"
            )
        return [
            PetriAnnotationExportItemDTO.from_entity(item)
            for item in self._item_repository.list_by_export_run_id(export_run_id)
        ]
