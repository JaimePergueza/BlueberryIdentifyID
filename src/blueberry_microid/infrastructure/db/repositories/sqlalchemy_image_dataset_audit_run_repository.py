from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.image_dataset_audit_run_repository import (
    ImageDatasetAuditRunRepositoryPort,
)
from blueberry_microid.domain.entities.image_dataset_audit_run import ImageDatasetAuditRun
from blueberry_microid.infrastructure.db.models.image_dataset_audit_run import ImageDatasetAuditRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import image_dataset_audit_run_to_entity


class SqlAlchemyImageDatasetAuditRunRepository(ImageDatasetAuditRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, audit_run: ImageDatasetAuditRun) -> ImageDatasetAuditRun:
        model = ImageDatasetAuditRunModel(
            id=audit_run.id,
            dataset_release_id=audit_run.dataset_release_id,
            status=audit_run.status.value,
            is_passed=audit_run.is_passed,
            total_items=audit_run.total_items,
            total_petri_images=audit_run.total_petri_images,
            total_micro_images=audit_run.total_micro_images,
            checked_petri_images=audit_run.checked_petri_images,
            checked_micro_images=audit_run.checked_micro_images,
            failed_petri_images=audit_run.failed_petri_images,
            failed_micro_images=audit_run.failed_micro_images,
            warning_count=audit_run.warning_count,
            error_count=audit_run.error_count,
            summary=audit_run.summary,
            format_distribution=audit_run.format_distribution,
            color_mode_distribution=audit_run.color_mode_distribution,
            dimension_distribution=audit_run.dimension_distribution,
            file_size_distribution=audit_run.file_size_distribution,
            created_at=audit_run.created_at,
            created_by=audit_run.created_by,
            notes=audit_run.notes,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return image_dataset_audit_run_to_entity(model)

    def get_by_id(self, audit_run_id: UUID) -> Optional[ImageDatasetAuditRun]:
        model = self._session.get(ImageDatasetAuditRunModel, audit_run_id)
        return image_dataset_audit_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[ImageDatasetAuditRun]:
        statement = select(ImageDatasetAuditRunModel).order_by(
            ImageDatasetAuditRunModel.created_at.asc(), ImageDatasetAuditRunModel.id.asc()
        )
        models = self._session.execute(statement).scalars().all()
        return [image_dataset_audit_run_to_entity(model) for model in models]

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[ImageDatasetAuditRun]:
        statement = (
            select(ImageDatasetAuditRunModel)
            .where(ImageDatasetAuditRunModel.dataset_release_id == dataset_release_id)
            .order_by(ImageDatasetAuditRunModel.created_at.asc(), ImageDatasetAuditRunModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [image_dataset_audit_run_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
