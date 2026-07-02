from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.human_review import HumanReview


class HumanReviewRepositoryPort(ABC):
    """Persistence boundary for expert HumanReview records.

    Implementations return domain entities, never ORM models. They preserve
    review history: adding a review never overwrites a Prediction and never
    deletes previous HumanReview rows.
    """

    @abstractmethod
    def add(self, human_review: HumanReview) -> HumanReview:
        """Persist a new review.

        Raises DuplicateFinalHumanReviewError if a final review already
        exists and the caller did not first demote it in the same transaction.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, human_review_id: UUID) -> Optional[HumanReview]:
        raise NotImplementedError

    @abstractmethod
    def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[HumanReview]:
        """Return reviews in chronological ascending order."""
        raise NotImplementedError

    @abstractmethod
    def get_final_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[HumanReview]:
        raise NotImplementedError

    @abstractmethod
    def unset_final_reviews_for_analysis_run(self, analysis_run_id: UUID) -> int:
        """Mark existing final reviews for the run as historical.

        Returns the number of rows updated.
        """
        raise NotImplementedError
