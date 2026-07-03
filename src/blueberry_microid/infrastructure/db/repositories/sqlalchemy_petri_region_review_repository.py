from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicateFinalPetriRegionReviewError
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.infrastructure.db.models.petri_region_review import PetriRegionReviewModel
from blueberry_microid.infrastructure.db.repositories.mappers import petri_region_review_to_entity


class SqlAlchemyPetriRegionReviewRepository(PetriRegionReviewRepositoryPort):
    """SQLAlchemy-backed PetriRegionReviewRepositoryPort.

    `auto_commit=False` is used inside UnitOfWork transactions so demoting
    the previous final review and adding the new one commit atomically.
    """

    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, review: PetriRegionReview) -> PetriRegionReview:
        model = PetriRegionReviewModel(
            id=review.id,
            petri_segmentation_region_id=review.petri_segmentation_region_id,
            petri_segmentation_run_id=review.petri_segmentation_run_id,
            dataset_release_id=review.dataset_release_id,
            dataset_item_id=review.dataset_item_id,
            dataset_split_item_id=review.dataset_split_item_id,
            decision=review.decision.value,
            reviewer_id=review.reviewer_id,
            reviewer_name=review.reviewer_name,
            confidence_score=review.confidence_score,
            is_final=review.is_final,
            corrected_bbox_x=review.corrected_bbox_x,
            corrected_bbox_y=review.corrected_bbox_y,
            corrected_bbox_width=review.corrected_bbox_width,
            corrected_bbox_height=review.corrected_bbox_height,
            corrected_notes=review.corrected_notes,
            review_notes=review.review_notes,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
        self._session.add(model)
        try:
            self._commit_or_flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateFinalPetriRegionReviewError(
                f"petri_segmentation_region '{review.petri_segmentation_region_id}' already has a final review"
            ) from exc
        self._session.refresh(model)
        return petri_region_review_to_entity(model)

    def get_by_id(self, review_id: UUID) -> Optional[PetriRegionReview]:
        model = self._session.get(PetriRegionReviewModel, review_id)
        return petri_region_review_to_entity(model) if model is not None else None

    def list_by_region_id(self, region_id: UUID) -> list[PetriRegionReview]:
        statement = (
            select(PetriRegionReviewModel)
            .where(PetriRegionReviewModel.petri_segmentation_region_id == region_id)
            .order_by(PetriRegionReviewModel.created_at.asc(), PetriRegionReviewModel.id.asc())
        )
        return [petri_region_review_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def list_by_segmentation_run_id(self, segmentation_run_id: UUID) -> list[PetriRegionReview]:
        statement = (
            select(PetriRegionReviewModel)
            .where(PetriRegionReviewModel.petri_segmentation_run_id == segmentation_run_id)
            .order_by(PetriRegionReviewModel.created_at.asc(), PetriRegionReviewModel.id.asc())
        )
        return [petri_region_review_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriRegionReview]:
        statement = (
            select(PetriRegionReviewModel)
            .where(PetriRegionReviewModel.dataset_release_id == dataset_release_id)
            .order_by(PetriRegionReviewModel.created_at.asc(), PetriRegionReviewModel.id.asc())
        )
        return [petri_region_review_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def get_final_by_region_id(self, region_id: UUID) -> Optional[PetriRegionReview]:
        statement = select(PetriRegionReviewModel).where(
            PetriRegionReviewModel.petri_segmentation_region_id == region_id,
            PetriRegionReviewModel.is_final.is_(True),
        )
        model = self._session.execute(statement).scalar_one_or_none()
        return petri_region_review_to_entity(model) if model is not None else None

    def unset_final_for_region(self, region_id: UUID) -> int:
        statement = (
            update(PetriRegionReviewModel)
            .where(
                PetriRegionReviewModel.petri_segmentation_region_id == region_id,
                PetriRegionReviewModel.is_final.is_(True),
            )
            .values(is_final=False)
        )
        result = self._session.execute(statement)
        self._commit_or_flush()
        return result.rowcount or 0

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
