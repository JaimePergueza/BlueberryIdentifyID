from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.infrastructure.db.models.annotation_bundle_run import AnnotationBundleRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import annotation_bundle_run_to_entity


class SqlAlchemyAnnotationBundleRunRepository(AnnotationBundleRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, bundle_run: AnnotationBundleRun) -> AnnotationBundleRun:
        model = AnnotationBundleRunModel(
            id=bundle_run.id,
            petri_annotation_export_run_id=bundle_run.petri_annotation_export_run_id,
            dataset_release_id=bundle_run.dataset_release_id,
            petri_segmentation_run_id=bundle_run.petri_segmentation_run_id,
            status=bundle_run.status.value,
            is_completed=bundle_run.is_completed,
            config=bundle_run.config,
            output_dir=bundle_run.output_dir,
            dry_run=bundle_run.dry_run,
            file_count=bundle_run.file_count,
            annotation_count=bundle_run.annotation_count,
            image_count=bundle_run.image_count,
            label_count=bundle_run.label_count,
            validation_summary=bundle_run.validation_summary,
            bundle_manifest=bundle_run.bundle_manifest,
            created_at=bundle_run.created_at,
            completed_at=bundle_run.completed_at,
            created_by=bundle_run.created_by,
            notes=bundle_run.notes,
            error_message=bundle_run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return annotation_bundle_run_to_entity(model)

    def get_by_id(self, bundle_run_id: UUID) -> Optional[AnnotationBundleRun]:
        model = self._session.get(AnnotationBundleRunModel, bundle_run_id)
        return annotation_bundle_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[AnnotationBundleRun]:
        return self._list(select(AnnotationBundleRunModel))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[AnnotationBundleRun]:
        return self._list(select(AnnotationBundleRunModel).where(AnnotationBundleRunModel.dataset_release_id == dataset_release_id))

    def list_by_petri_annotation_export_run_id(self, export_run_id: UUID) -> list[AnnotationBundleRun]:
        return self._list(select(AnnotationBundleRunModel).where(AnnotationBundleRunModel.petri_annotation_export_run_id == export_run_id))

    def _list(self, statement) -> list[AnnotationBundleRun]:
        statement = statement.order_by(AnnotationBundleRunModel.created_at.asc(), AnnotationBundleRunModel.id.asc())
        return [annotation_bundle_run_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
