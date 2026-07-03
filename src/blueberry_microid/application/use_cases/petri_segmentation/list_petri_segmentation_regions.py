from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.petri_segmentation_dto import PetriSegmentationRegionDTO
from blueberry_microid.application.exceptions import PetriSegmentationRunNotFoundError
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.application.ports.petri_segmentation_run_repository import PetriSegmentationRunRepositoryPort
from blueberry_microid.domain.enums.dataset_split import DatasetSplit


class ListPetriSegmentationRegionsUseCase:
    def __init__(
        self,
        run_repository: PetriSegmentationRunRepositoryPort,
        region_repository: PetriSegmentationRegionRepositoryPort,
    ) -> None:
        self._run_repository = run_repository
        self._region_repository = region_repository

    def execute(
        self, segmentation_run_id: UUID, *, split: Optional[DatasetSplit] = None
    ) -> list[PetriSegmentationRegionDTO]:
        if self._run_repository.get_by_id(segmentation_run_id) is None:
            raise PetriSegmentationRunNotFoundError(
                f"petri_segmentation_run '{segmentation_run_id}' does not exist"
            )
        regions = (
            self._region_repository.list_by_segmentation_run_id_and_split(segmentation_run_id, split)
            if split is not None
            else self._region_repository.list_by_segmentation_run_id(segmentation_run_id)
        )
        return [PetriSegmentationRegionDTO.from_entity(region) for region in regions]
