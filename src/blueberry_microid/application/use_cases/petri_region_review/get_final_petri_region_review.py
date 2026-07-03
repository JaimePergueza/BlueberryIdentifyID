from uuid import UUID

from blueberry_microid.application.dto.petri_region_review_dto import PetriRegionReviewDTO
from blueberry_microid.application.exceptions import (
    PetriRegionReviewNotFoundError,
    PetriSegmentationRegionNotFoundError,
)
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)


class GetFinalPetriRegionReviewUseCase:
    """Return the current vigente review for a PetriSegmentationRegion."""

    def __init__(
        self,
        region_repository: PetriSegmentationRegionRepositoryPort,
        review_repository: PetriRegionReviewRepositoryPort,
    ) -> None:
        self._region_repository = region_repository
        self._review_repository = review_repository

    def execute(self, region_id: UUID) -> PetriRegionReviewDTO:
        if self._region_repository.get_by_id(region_id) is None:
            raise PetriSegmentationRegionNotFoundError(f"petri_segmentation_region '{region_id}' does not exist")

        review = self._review_repository.get_final_by_region_id(region_id)
        if review is None:
            raise PetriRegionReviewNotFoundError(
                f"final petri_region_review for petri_segmentation_region '{region_id}' does not exist"
            )
        return PetriRegionReviewDTO.from_entity(review)
