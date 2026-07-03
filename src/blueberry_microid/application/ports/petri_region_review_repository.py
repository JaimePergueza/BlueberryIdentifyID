from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview


class PetriRegionReviewRepositoryPort(ABC):
    @abstractmethod
    def add(self, review: PetriRegionReview) -> PetriRegionReview:
        """Persist a new PetriRegionReview.

        Raises DuplicateFinalPetriRegionReviewError if a final review already
        exists for the region and the caller did not first demote it in the
        same transaction.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, review_id: UUID) -> Optional[PetriRegionReview]:
        raise NotImplementedError

    @abstractmethod
    def list_by_region_id(self, region_id: UUID) -> list[PetriRegionReview]:
        """Return reviews in chronological ascending order."""
        raise NotImplementedError

    @abstractmethod
    def list_by_segmentation_run_id(self, segmentation_run_id: UUID) -> list[PetriRegionReview]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriRegionReview]:
        raise NotImplementedError

    @abstractmethod
    def get_final_by_region_id(self, region_id: UUID) -> Optional[PetriRegionReview]:
        raise NotImplementedError

    @abstractmethod
    def unset_final_for_region(self, region_id: UUID) -> int:
        """Mark existing final reviews for the region as historical.

        Returns the number of rows updated.
        """
        raise NotImplementedError
