from uuid import UUID

from blueberry_microid.application.dto.petri_region_review_dto import PetriRegionReviewDTO
from blueberry_microid.application.exceptions import (
    DatasetReleaseNotFoundError,
    PetriSegmentationRegionNotFoundError,
    PetriSegmentationRunNotFoundError,
)
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.application.ports.petri_segmentation_run_repository import PetriSegmentationRunRepositoryPort


class ListPetriRegionReviewsUseCase:
    """List PetriRegionReview history by region, segmentation run, or dataset release."""

    def __init__(
        self,
        region_repository: PetriSegmentationRegionRepositoryPort,
        segmentation_run_repository: PetriSegmentationRunRepositoryPort,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        review_repository: PetriRegionReviewRepositoryPort,
    ) -> None:
        self._region_repository = region_repository
        self._segmentation_run_repository = segmentation_run_repository
        self._dataset_release_repository = dataset_release_repository
        self._review_repository = review_repository

    def by_region(self, region_id: UUID) -> list[PetriRegionReviewDTO]:
        if self._region_repository.get_by_id(region_id) is None:
            raise PetriSegmentationRegionNotFoundError(f"petri_segmentation_region '{region_id}' does not exist")
        return [
            PetriRegionReviewDTO.from_entity(review)
            for review in self._review_repository.list_by_region_id(region_id)
        ]

    def by_segmentation_run(self, segmentation_run_id: UUID) -> list[PetriRegionReviewDTO]:
        if self._segmentation_run_repository.get_by_id(segmentation_run_id) is None:
            raise PetriSegmentationRunNotFoundError(f"petri_segmentation_run '{segmentation_run_id}' does not exist")
        return [
            PetriRegionReviewDTO.from_entity(review)
            for review in self._review_repository.list_by_segmentation_run_id(segmentation_run_id)
        ]

    def by_dataset_release(self, dataset_release_id: UUID) -> list[PetriRegionReviewDTO]:
        if self._dataset_release_repository.get_by_id(dataset_release_id) is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{dataset_release_id}' does not exist")
        return [
            PetriRegionReviewDTO.from_entity(review)
            for review in self._review_repository.list_by_dataset_release_id(dataset_release_id)
        ]
