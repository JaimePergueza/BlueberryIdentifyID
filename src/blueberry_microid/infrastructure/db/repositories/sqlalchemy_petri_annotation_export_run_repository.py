from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.petri_annotation_export_run_repository import (
    PetriAnnotationExportRunRepositoryPort,
)
from blueberry_microid.domain.entities.petri_annotation_export_run import PetriAnnotationExportRun
from blueberry_microid.infrastructure.db.models.petri_annotation_export_run import PetriAnnotationExportRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import petri_annotation_export_run_to_entity


class SqlAlchemyPetriAnnotationExportRunRepository(PetriAnnotationExportRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, export_run: PetriAnnotationExportRun) -> PetriAnnotationExportRun:
        model = PetriAnnotationExportRunModel(
            id=export_run.id,
            dataset_release_id=export_run.dataset_release_id,
            petri_segmentation_run_id=export_run.petri_segmentation_run_id,
            export_format=export_run.export_format.value,
            status=export_run.status.value,
            is_completed=export_run.is_completed,
            config=export_run.config,
            exported_annotation_count=export_run.exported_annotation_count,
            skipped_review_count=export_run.skipped_review_count,
            image_count=export_run.image_count,
            category_count=export_run.category_count,
            output_manifest=export_run.output_manifest,
            summary=export_run.summary,
            created_at=export_run.created_at,
            completed_at=export_run.completed_at,
            created_by=export_run.created_by,
            notes=export_run.notes,
            error_message=export_run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return petri_annotation_export_run_to_entity(model)

    def get_by_id(self, export_run_id: UUID) -> Optional[PetriAnnotationExportRun]:
        model = self._session.get(PetriAnnotationExportRunModel, export_run_id)
        return petri_annotation_export_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[PetriAnnotationExportRun]:
        statement = select(PetriAnnotationExportRunModel).order_by(
            PetriAnnotationExportRunModel.created_at.asc(), PetriAnnotationExportRunModel.id.asc()
        )
        return [petri_annotation_export_run_to_entity(model) for model in self._session.execute(statement).scalars()]

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriAnnotationExportRun]:
        statement = (
            select(PetriAnnotationExportRunModel)
            .where(PetriAnnotationExportRunModel.dataset_release_id == dataset_release_id)
            .order_by(PetriAnnotationExportRunModel.created_at.asc(), PetriAnnotationExportRunModel.id.asc())
        )
        return [petri_annotation_export_run_to_entity(model) for model in self._session.execute(statement).scalars()]

    def list_by_petri_segmentation_run_id(self, petri_segmentation_run_id: UUID) -> list[PetriAnnotationExportRun]:
        statement = (
            select(PetriAnnotationExportRunModel)
            .where(PetriAnnotationExportRunModel.petri_segmentation_run_id == petri_segmentation_run_id)
            .order_by(PetriAnnotationExportRunModel.created_at.asc(), PetriAnnotationExportRunModel.id.asc())
        )
        return [petri_annotation_export_run_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
