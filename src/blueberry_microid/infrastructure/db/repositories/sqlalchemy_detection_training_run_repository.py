from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.infrastructure.db.models.detection_training_run import DetectionTrainingRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_run_to_entity


class SqlAlchemyDetectionTrainingRunRepository(DetectionTrainingRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, run: DetectionTrainingRun) -> DetectionTrainingRun:
        model = DetectionTrainingRunModel(
            id=run.id,
            annotation_bundle_run_id=run.annotation_bundle_run_id,
            annotation_quality_gate_run_id=run.annotation_quality_gate_run_id,
            dataset_release_id=run.dataset_release_id,
            petri_annotation_export_run_id=run.petri_annotation_export_run_id,
            algorithm=run.algorithm.value,
            mode=run.mode.value,
            status=run.status.value,
            is_runnable=run.is_runnable,
            config=run.config,
            training_plan=run.training_plan,
            command_preview=run.command_preview,
            dataset_summary=run.dataset_summary,
            quality_gate_summary=run.quality_gate_summary,
            expected_outputs=run.expected_outputs,
            issue_count=run.issue_count,
            warning_count=run.warning_count,
            error_count=run.error_count,
            created_at=run.created_at,
            completed_at=run.completed_at,
            created_by=run.created_by,
            notes=run.notes,
            error_message=run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return detection_training_run_to_entity(model)

    def get_by_id(self, run_id: UUID) -> Optional[DetectionTrainingRun]:
        model = self._session.get(DetectionTrainingRunModel, run_id)
        return detection_training_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[DetectionTrainingRun]:
        return self._list(select(DetectionTrainingRunModel))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingRun]:
        return self._list(
            select(DetectionTrainingRunModel).where(
                DetectionTrainingRunModel.dataset_release_id == dataset_release_id
            )
        )

    def list_by_annotation_bundle_run_id(self, annotation_bundle_run_id: UUID) -> list[DetectionTrainingRun]:
        return self._list(
            select(DetectionTrainingRunModel).where(
                DetectionTrainingRunModel.annotation_bundle_run_id == annotation_bundle_run_id
            )
        )

    def list_by_annotation_quality_gate_run_id(
        self, annotation_quality_gate_run_id: UUID
    ) -> list[DetectionTrainingRun]:
        return self._list(
            select(DetectionTrainingRunModel).where(
                DetectionTrainingRunModel.annotation_quality_gate_run_id == annotation_quality_gate_run_id
            )
        )

    def _list(self, statement) -> list[DetectionTrainingRun]:
        statement = statement.order_by(
            DetectionTrainingRunModel.created_at.asc(),
            DetectionTrainingRunModel.id.asc(),
        )
        return [detection_training_run_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
