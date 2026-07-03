from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.petri_segmentation_dto import PetriSegmentationRunDTO
from blueberry_microid.application.ports.petri_segmentation_run_repository import PetriSegmentationRunRepositoryPort


class ListPetriSegmentationRunsUseCase:
    def __init__(self, run_repository: PetriSegmentationRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(
        self,
        *,
        dataset_release_id: Optional[UUID] = None,
        image_audit_run_id: Optional[UUID] = None,
    ) -> list[PetriSegmentationRunDTO]:
        if dataset_release_id is not None:
            runs = self._run_repository.list_by_dataset_release_id(dataset_release_id)
        elif image_audit_run_id is not None:
            runs = self._run_repository.list_by_image_audit_run_id(image_audit_run_id)
        else:
            runs = self._run_repository.list_all()
        return [PetriSegmentationRunDTO.from_entity(run) for run in runs]
