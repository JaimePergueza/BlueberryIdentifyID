from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.petri_segmentation_run_repository import (
    PetriSegmentationRunRepositoryPort,
)
from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun
from blueberry_microid.infrastructure.db.models.petri_segmentation_run import PetriSegmentationRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import petri_segmentation_run_to_entity


class SqlAlchemyPetriSegmentationRunRepository(PetriSegmentationRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, segmentation_run: PetriSegmentationRun) -> PetriSegmentationRun:
        model = PetriSegmentationRunModel(
            id=segmentation_run.id,
            dataset_release_id=segmentation_run.dataset_release_id,
            image_audit_run_id=segmentation_run.image_audit_run_id,
            status=segmentation_run.status.value,
            is_completed=segmentation_run.is_completed,
            config=segmentation_run.config,
            total_items=segmentation_run.total_items,
            processed_petri_images=segmentation_run.processed_petri_images,
            failed_petri_images=segmentation_run.failed_petri_images,
            total_regions_detected=segmentation_run.total_regions_detected,
            mean_regions_per_image=segmentation_run.mean_regions_per_image,
            summary=segmentation_run.summary,
            started_at=segmentation_run.started_at,
            completed_at=segmentation_run.completed_at,
            created_at=segmentation_run.created_at,
            created_by=segmentation_run.created_by,
            notes=segmentation_run.notes,
            error_message=segmentation_run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return petri_segmentation_run_to_entity(model)

    def get_by_id(self, segmentation_run_id: UUID) -> Optional[PetriSegmentationRun]:
        model = self._session.get(PetriSegmentationRunModel, segmentation_run_id)
        return petri_segmentation_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[PetriSegmentationRun]:
        statement = select(PetriSegmentationRunModel).order_by(
            PetriSegmentationRunModel.created_at.asc(), PetriSegmentationRunModel.id.asc()
        )
        return [petri_segmentation_run_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriSegmentationRun]:
        statement = (
            select(PetriSegmentationRunModel)
            .where(PetriSegmentationRunModel.dataset_release_id == dataset_release_id)
            .order_by(PetriSegmentationRunModel.created_at.asc(), PetriSegmentationRunModel.id.asc())
        )
        return [petri_segmentation_run_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def list_by_image_audit_run_id(self, image_audit_run_id: UUID) -> list[PetriSegmentationRun]:
        statement = (
            select(PetriSegmentationRunModel)
            .where(PetriSegmentationRunModel.image_audit_run_id == image_audit_run_id)
            .order_by(PetriSegmentationRunModel.created_at.asc(), PetriSegmentationRunModel.id.asc())
        )
        return [petri_segmentation_run_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
