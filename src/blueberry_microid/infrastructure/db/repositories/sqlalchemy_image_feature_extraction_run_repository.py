from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.image_feature_extraction_run_repository import (
    ImageFeatureExtractionRunRepositoryPort,
)
from blueberry_microid.domain.entities.image_feature_extraction_run import ImageFeatureExtractionRun
from blueberry_microid.infrastructure.db.models.image_feature_extraction_run import ImageFeatureExtractionRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import image_feature_extraction_run_to_entity


class SqlAlchemyImageFeatureExtractionRunRepository(ImageFeatureExtractionRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, extraction_run: ImageFeatureExtractionRun) -> ImageFeatureExtractionRun:
        model = ImageFeatureExtractionRunModel(
            id=extraction_run.id,
            dataset_release_id=extraction_run.dataset_release_id,
            image_audit_run_id=extraction_run.image_audit_run_id,
            status=extraction_run.status.value,
            is_completed=extraction_run.is_completed,
            config=extraction_run.config,
            total_items=extraction_run.total_items,
            processed_items=extraction_run.processed_items,
            failed_items=extraction_run.failed_items,
            total_feature_vectors=extraction_run.total_feature_vectors,
            petri_feature_count=extraction_run.petri_feature_count,
            micro_feature_count=extraction_run.micro_feature_count,
            summary=extraction_run.summary,
            started_at=extraction_run.started_at,
            completed_at=extraction_run.completed_at,
            created_at=extraction_run.created_at,
            created_by=extraction_run.created_by,
            notes=extraction_run.notes,
            error_message=extraction_run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return image_feature_extraction_run_to_entity(model)

    def get_by_id(self, extraction_run_id: UUID) -> Optional[ImageFeatureExtractionRun]:
        model = self._session.get(ImageFeatureExtractionRunModel, extraction_run_id)
        return image_feature_extraction_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[ImageFeatureExtractionRun]:
        statement = select(ImageFeatureExtractionRunModel).order_by(
            ImageFeatureExtractionRunModel.created_at.asc(), ImageFeatureExtractionRunModel.id.asc()
        )
        models = self._session.execute(statement).scalars().all()
        return [image_feature_extraction_run_to_entity(model) for model in models]

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[ImageFeatureExtractionRun]:
        statement = (
            select(ImageFeatureExtractionRunModel)
            .where(ImageFeatureExtractionRunModel.dataset_release_id == dataset_release_id)
            .order_by(ImageFeatureExtractionRunModel.created_at.asc(), ImageFeatureExtractionRunModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [image_feature_extraction_run_to_entity(model) for model in models]

    def list_by_image_audit_run_id(self, image_audit_run_id: UUID) -> list[ImageFeatureExtractionRun]:
        statement = (
            select(ImageFeatureExtractionRunModel)
            .where(ImageFeatureExtractionRunModel.image_audit_run_id == image_audit_run_id)
            .order_by(ImageFeatureExtractionRunModel.created_at.asc(), ImageFeatureExtractionRunModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [image_feature_extraction_run_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
