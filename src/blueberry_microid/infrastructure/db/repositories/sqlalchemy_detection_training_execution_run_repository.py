from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_execution_run_repository import (
    DetectionTrainingExecutionRunRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_execution_run import DetectionTrainingExecutionRun
from blueberry_microid.infrastructure.db.models.detection_training_execution_run import (
    DetectionTrainingExecutionRunModel,
)
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_execution_run_to_entity


class SqlAlchemyDetectionTrainingExecutionRunRepository(DetectionTrainingExecutionRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, run: DetectionTrainingExecutionRun) -> DetectionTrainingExecutionRun:
        model = DetectionTrainingExecutionRunModel(
            id=run.id,
            detection_training_run_id=run.detection_training_run_id,
            readiness_report_id=run.readiness_report_id,
            environment_spec_id=run.environment_spec_id,
            artifact_policy_id=run.artifact_policy_id,
            annotation_bundle_run_id=run.annotation_bundle_run_id,
            dataset_release_id=run.dataset_release_id,
            status=run.status.value,
            decision=run.decision.value,
            mode=run.mode.value,
            is_executable=run.is_executable,
            config=run.config,
            prerequisite_summary=run.prerequisite_summary,
            repository_safety_summary=run.repository_safety_summary,
            execution_plan=run.execution_plan,
            command_preview=run.command_preview,
            expected_outputs=run.expected_outputs,
            risk_summary=run.risk_summary,
            recommendation_summary=run.recommendation_summary,
            error_count=run.error_count,
            warning_count=run.warning_count,
            info_count=run.info_count,
            created_at=run.created_at,
            completed_at=run.completed_at,
            created_by=run.created_by,
            notes=run.notes,
            error_message=run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return detection_training_execution_run_to_entity(model)

    def get_by_id(self, execution_run_id: UUID) -> Optional[DetectionTrainingExecutionRun]:
        model = self._session.get(DetectionTrainingExecutionRunModel, execution_run_id)
        return detection_training_execution_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[DetectionTrainingExecutionRun]:
        return self._list(select(DetectionTrainingExecutionRunModel))

    def list_by_detection_training_run_id(
        self, detection_training_run_id: UUID
    ) -> list[DetectionTrainingExecutionRun]:
        return self._list(
            select(DetectionTrainingExecutionRunModel).where(
                DetectionTrainingExecutionRunModel.detection_training_run_id == detection_training_run_id
            )
        )

    def list_by_readiness_report_id(self, readiness_report_id: UUID) -> list[DetectionTrainingExecutionRun]:
        return self._list(
            select(DetectionTrainingExecutionRunModel).where(
                DetectionTrainingExecutionRunModel.readiness_report_id == readiness_report_id
            )
        )

    def list_by_environment_spec_id(self, environment_spec_id: UUID) -> list[DetectionTrainingExecutionRun]:
        return self._list(
            select(DetectionTrainingExecutionRunModel).where(
                DetectionTrainingExecutionRunModel.environment_spec_id == environment_spec_id
            )
        )

    def list_by_artifact_policy_id(self, artifact_policy_id: UUID) -> list[DetectionTrainingExecutionRun]:
        return self._list(
            select(DetectionTrainingExecutionRunModel).where(
                DetectionTrainingExecutionRunModel.artifact_policy_id == artifact_policy_id
            )
        )

    def list_by_annotation_bundle_run_id(
        self, annotation_bundle_run_id: UUID
    ) -> list[DetectionTrainingExecutionRun]:
        return self._list(
            select(DetectionTrainingExecutionRunModel).where(
                DetectionTrainingExecutionRunModel.annotation_bundle_run_id == annotation_bundle_run_id
            )
        )

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingExecutionRun]:
        return self._list(
            select(DetectionTrainingExecutionRunModel).where(
                DetectionTrainingExecutionRunModel.dataset_release_id == dataset_release_id
            )
        )

    def _list(self, statement) -> list[DetectionTrainingExecutionRun]:
        statement = statement.order_by(
            DetectionTrainingExecutionRunModel.created_at.asc(),
            DetectionTrainingExecutionRunModel.id.asc(),
        )
        return [
            detection_training_execution_run_to_entity(model)
            for model in self._session.execute(statement).scalars()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
