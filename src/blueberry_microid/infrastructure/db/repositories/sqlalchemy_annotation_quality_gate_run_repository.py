from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.annotation_quality_gate_run_repository import (
    AnnotationQualityGateRunRepositoryPort,
)
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.infrastructure.db.models.annotation_quality_gate_run import AnnotationQualityGateRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import annotation_quality_gate_run_to_entity


class SqlAlchemyAnnotationQualityGateRunRepository(AnnotationQualityGateRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, quality_gate_run: AnnotationQualityGateRun) -> AnnotationQualityGateRun:
        model = AnnotationQualityGateRunModel(
            id=quality_gate_run.id,
            annotation_bundle_run_id=quality_gate_run.annotation_bundle_run_id,
            dataset_release_id=quality_gate_run.dataset_release_id,
            petri_annotation_export_run_id=quality_gate_run.petri_annotation_export_run_id,
            status=quality_gate_run.status.value,
            is_passed=quality_gate_run.is_passed,
            config=quality_gate_run.config,
            total_images=quality_gate_run.total_images,
            total_annotations=quality_gate_run.total_annotations,
            train_image_count=quality_gate_run.train_image_count,
            validation_image_count=quality_gate_run.validation_image_count,
            test_image_count=quality_gate_run.test_image_count,
            train_annotation_count=quality_gate_run.train_annotation_count,
            validation_annotation_count=quality_gate_run.validation_annotation_count,
            test_annotation_count=quality_gate_run.test_annotation_count,
            error_count=quality_gate_run.error_count,
            warning_count=quality_gate_run.warning_count,
            quality_summary=quality_gate_run.quality_summary,
            split_distribution=quality_gate_run.split_distribution,
            bbox_statistics=quality_gate_run.bbox_statistics,
            category_distribution=quality_gate_run.category_distribution,
            created_at=quality_gate_run.created_at,
            completed_at=quality_gate_run.completed_at,
            created_by=quality_gate_run.created_by,
            notes=quality_gate_run.notes,
            error_message=quality_gate_run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return annotation_quality_gate_run_to_entity(model)

    def get_by_id(self, quality_gate_run_id: UUID) -> Optional[AnnotationQualityGateRun]:
        model = self._session.get(AnnotationQualityGateRunModel, quality_gate_run_id)
        return annotation_quality_gate_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[AnnotationQualityGateRun]:
        return self._list(select(AnnotationQualityGateRunModel))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[AnnotationQualityGateRun]:
        return self._list(
            select(AnnotationQualityGateRunModel).where(
                AnnotationQualityGateRunModel.dataset_release_id == dataset_release_id
            )
        )

    def list_by_annotation_bundle_run_id(self, annotation_bundle_run_id: UUID) -> list[AnnotationQualityGateRun]:
        return self._list(
            select(AnnotationQualityGateRunModel).where(
                AnnotationQualityGateRunModel.annotation_bundle_run_id == annotation_bundle_run_id
            )
        )

    def _list(self, statement) -> list[AnnotationQualityGateRun]:
        statement = statement.order_by(
            AnnotationQualityGateRunModel.created_at.asc(),
            AnnotationQualityGateRunModel.id.asc(),
        )
        return [annotation_quality_gate_run_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
