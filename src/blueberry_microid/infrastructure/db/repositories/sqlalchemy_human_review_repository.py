from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicateFinalHumanReviewError
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
from blueberry_microid.infrastructure.db.repositories.mappers import human_review_to_entity


class SqlAlchemyHumanReviewRepository(HumanReviewRepositoryPort):
    """SQLAlchemy-backed HumanReviewRepositoryPort.

    `auto_commit=False` is used inside UnitOfWork transactions so demoting
    the previous final review and adding the new one commit atomically.
    """

    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, human_review: HumanReview) -> HumanReview:
        model = HumanReviewModel(
            id=human_review.id,
            analysis_run_id=human_review.analysis_run_id,
            reviewer_name=human_review.reviewer_name,
            review_decision=human_review.review_decision,
            corrected_label=human_review.corrected_label,
            comments=human_review.comments,
            is_final=human_review.is_final,
            created_at=human_review.created_at,
        )
        self._session.add(model)
        try:
            self._commit_or_flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateFinalHumanReviewError(
                f"analysis_run '{human_review.analysis_run_id}' already has a final human review"
            ) from exc
        self._session.refresh(model)
        return human_review_to_entity(model)

    def get_by_id(self, human_review_id: UUID) -> Optional[HumanReview]:
        model = self._session.get(HumanReviewModel, human_review_id)
        return human_review_to_entity(model) if model is not None else None

    def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[HumanReview]:
        statement = (
            select(HumanReviewModel)
            .where(HumanReviewModel.analysis_run_id == analysis_run_id)
            .order_by(HumanReviewModel.created_at.asc(), HumanReviewModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [human_review_to_entity(model) for model in models]

    def get_final_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[HumanReview]:
        statement = select(HumanReviewModel).where(
            HumanReviewModel.analysis_run_id == analysis_run_id,
            HumanReviewModel.is_final.is_(True),
        )
        model = self._session.execute(statement).scalar_one_or_none()
        return human_review_to_entity(model) if model is not None else None

    def unset_final_reviews_for_analysis_run(self, analysis_run_id: UUID) -> int:
        statement = (
            update(HumanReviewModel)
            .where(HumanReviewModel.analysis_run_id == analysis_run_id, HumanReviewModel.is_final.is_(True))
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
