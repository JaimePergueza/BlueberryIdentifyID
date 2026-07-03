from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.petri_annotation_export_dto import PetriAnnotationExportRunDTO
from blueberry_microid.application.ports.petri_annotation_export_run_repository import (
    PetriAnnotationExportRunRepositoryPort,
)


class ListPetriAnnotationExportRunsUseCase:
    def __init__(self, run_repository: PetriAnnotationExportRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(
        self,
        *,
        dataset_release_id: Optional[UUID] = None,
        petri_segmentation_run_id: Optional[UUID] = None,
    ) -> list[PetriAnnotationExportRunDTO]:
        if dataset_release_id is not None:
            runs = self._run_repository.list_by_dataset_release_id(dataset_release_id)
        elif petri_segmentation_run_id is not None:
            runs = self._run_repository.list_by_petri_segmentation_run_id(petri_segmentation_run_id)
        else:
            runs = self._run_repository.list_all()
        return [PetriAnnotationExportRunDTO.from_entity(run) for run in runs]
