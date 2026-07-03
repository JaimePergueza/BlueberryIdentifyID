from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_environment_spec_repository import (
    DetectionTrainingEnvironmentSpecRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec
from blueberry_microid.infrastructure.db.models.detection_training_environment_spec import (
    DetectionTrainingEnvironmentSpecModel,
)
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_environment_spec_to_entity


class SqlAlchemyDetectionTrainingEnvironmentSpecRepository(DetectionTrainingEnvironmentSpecRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, spec: DetectionTrainingEnvironmentSpec) -> DetectionTrainingEnvironmentSpec:
        model = DetectionTrainingEnvironmentSpecModel(
            id=spec.id,
            detection_training_run_id=spec.detection_training_run_id,
            readiness_report_id=spec.readiness_report_id,
            annotation_bundle_run_id=spec.annotation_bundle_run_id,
            dataset_release_id=spec.dataset_release_id,
            decision=spec.decision.value,
            status=spec.status.value,
            is_environment_ready=spec.is_environment_ready,
            config=spec.config,
            detected_environment=spec.detected_environment,
            dependency_policy=spec.dependency_policy,
            hardware_policy=spec.hardware_policy,
            artifact_policy=spec.artifact_policy,
            execution_policy=spec.execution_policy,
            setup_instructions=spec.setup_instructions,
            safe_check_summary=spec.safe_check_summary,
            risk_summary=spec.risk_summary,
            recommendation_summary=spec.recommendation_summary,
            error_count=spec.error_count,
            warning_count=spec.warning_count,
            info_count=spec.info_count,
            created_at=spec.created_at,
            completed_at=spec.completed_at,
            created_by=spec.created_by,
            notes=spec.notes,
            error_message=spec.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return detection_training_environment_spec_to_entity(model)

    def get_by_id(self, spec_id: UUID) -> Optional[DetectionTrainingEnvironmentSpec]:
        model = self._session.get(DetectionTrainingEnvironmentSpecModel, spec_id)
        return detection_training_environment_spec_to_entity(model) if model is not None else None

    def list_all(self) -> list[DetectionTrainingEnvironmentSpec]:
        return self._list(select(DetectionTrainingEnvironmentSpecModel))

    def list_by_detection_training_run_id(
        self, detection_training_run_id: UUID
    ) -> list[DetectionTrainingEnvironmentSpec]:
        return self._list(
            select(DetectionTrainingEnvironmentSpecModel).where(
                DetectionTrainingEnvironmentSpecModel.detection_training_run_id == detection_training_run_id
            )
        )

    def list_by_readiness_report_id(self, readiness_report_id: UUID) -> list[DetectionTrainingEnvironmentSpec]:
        return self._list(
            select(DetectionTrainingEnvironmentSpecModel).where(
                DetectionTrainingEnvironmentSpecModel.readiness_report_id == readiness_report_id
            )
        )

    def list_by_annotation_bundle_run_id(
        self, annotation_bundle_run_id: UUID
    ) -> list[DetectionTrainingEnvironmentSpec]:
        return self._list(
            select(DetectionTrainingEnvironmentSpecModel).where(
                DetectionTrainingEnvironmentSpecModel.annotation_bundle_run_id == annotation_bundle_run_id
            )
        )

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingEnvironmentSpec]:
        return self._list(
            select(DetectionTrainingEnvironmentSpecModel).where(
                DetectionTrainingEnvironmentSpecModel.dataset_release_id == dataset_release_id
            )
        )

    def _list(self, statement) -> list[DetectionTrainingEnvironmentSpec]:
        statement = statement.order_by(
            DetectionTrainingEnvironmentSpecModel.created_at.asc(),
            DetectionTrainingEnvironmentSpecModel.id.asc(),
        )
        return [
            detection_training_environment_spec_to_entity(model)
            for model in self._session.execute(statement).scalars()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
