from uuid import UUID

from blueberry_microid.application.dto.petri_region_review_dto import PetriRegionReviewDTO
from blueberry_microid.application.exceptions import PetriRegionReviewNotFoundError
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort


class GetPetriRegionReviewUseCase:
    """Return a single PetriRegionReview by id."""

    def __init__(self, review_repository: PetriRegionReviewRepositoryPort) -> None:
        self._review_repository = review_repository

    def execute(self, review_id: UUID) -> PetriRegionReviewDTO:
        review = self._review_repository.get_by_id(review_id)
        if review is None:
            raise PetriRegionReviewNotFoundError(f"petri_region_review '{review_id}' does not exist")
        return PetriRegionReviewDTO.from_entity(review)
