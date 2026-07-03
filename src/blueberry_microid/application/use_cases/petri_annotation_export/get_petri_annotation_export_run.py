from uuid import UUID

from blueberry_microid.application.dto.petri_annotation_export_dto import PetriAnnotationExportRunDTO
from blueberry_microid.application.exceptions import PetriAnnotationExportRunNotFoundError
from blueberry_microid.application.ports.petri_annotation_export_run_repository import (
    PetriAnnotationExportRunRepositoryPort,
)


class GetPetriAnnotationExportRunUseCase:
    def __init__(self, run_repository: PetriAnnotationExportRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(self, export_run_id: UUID) -> PetriAnnotationExportRunDTO:
        run = self._run_repository.get_by_id(export_run_id)
        if run is None:
            raise PetriAnnotationExportRunNotFoundError(
                f"petri_annotation_export_run '{export_run_id}' does not exist"
            )
        return PetriAnnotationExportRunDTO.from_entity(run)
