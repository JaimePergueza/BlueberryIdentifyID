from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_artifact_policy_repository import (
    DetectionTrainingArtifactPolicyRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_artifact_policy import DetectionTrainingArtifactPolicy
from blueberry_microid.infrastructure.db.models.detection_training_artifact_policy import (
    DetectionTrainingArtifactPolicyModel,
)
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_artifact_policy_to_entity


class SqlAlchemyDetectionTrainingArtifactPolicyRepository(DetectionTrainingArtifactPolicyRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, policy: DetectionTrainingArtifactPolicy) -> DetectionTrainingArtifactPolicy:
        model = DetectionTrainingArtifactPolicyModel(
            id=policy.id,
            detection_training_run_id=policy.detection_training_run_id,
            readiness_report_id=policy.readiness_report_id,
            environment_spec_id=policy.environment_spec_id,
            annotation_bundle_run_id=policy.annotation_bundle_run_id,
            dataset_release_id=policy.dataset_release_id,
            decision=policy.decision.value,
            status=policy.status.value,
            is_policy_ready=policy.is_policy_ready,
            config=policy.config,
            artifact_root_dir=policy.artifact_root_dir,
            planned_output_summary=policy.planned_output_summary,
            storage_policy=policy.storage_policy,
            git_policy=policy.git_policy,
            checksum_policy=policy.checksum_policy,
            registry_summary=policy.registry_summary,
            risk_summary=policy.risk_summary,
            recommendation_summary=policy.recommendation_summary,
            error_count=policy.error_count,
            warning_count=policy.warning_count,
            info_count=policy.info_count,
            created_at=policy.created_at,
            completed_at=policy.completed_at,
            created_by=policy.created_by,
            notes=policy.notes,
            error_message=policy.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return detection_training_artifact_policy_to_entity(model)

    def get_by_id(self, policy_id: UUID) -> Optional[DetectionTrainingArtifactPolicy]:
        model = self._session.get(DetectionTrainingArtifactPolicyModel, policy_id)
        return detection_training_artifact_policy_to_entity(model) if model is not None else None

    def list_all(self) -> list[DetectionTrainingArtifactPolicy]:
        return self._list(select(DetectionTrainingArtifactPolicyModel))

    def list_by_detection_training_run_id(
        self, detection_training_run_id: UUID
    ) -> list[DetectionTrainingArtifactPolicy]:
        return self._list(
            select(DetectionTrainingArtifactPolicyModel).where(
                DetectionTrainingArtifactPolicyModel.detection_training_run_id == detection_training_run_id
            )
        )

    def list_by_readiness_report_id(self, readiness_report_id: UUID) -> list[DetectionTrainingArtifactPolicy]:
        return self._list(
            select(DetectionTrainingArtifactPolicyModel).where(
                DetectionTrainingArtifactPolicyModel.readiness_report_id == readiness_report_id
            )
        )

    def list_by_environment_spec_id(self, environment_spec_id: UUID) -> list[DetectionTrainingArtifactPolicy]:
        return self._list(
            select(DetectionTrainingArtifactPolicyModel).where(
                DetectionTrainingArtifactPolicyModel.environment_spec_id == environment_spec_id
            )
        )

    def list_by_annotation_bundle_run_id(
        self, annotation_bundle_run_id: UUID
    ) -> list[DetectionTrainingArtifactPolicy]:
        return self._list(
            select(DetectionTrainingArtifactPolicyModel).where(
                DetectionTrainingArtifactPolicyModel.annotation_bundle_run_id == annotation_bundle_run_id
            )
        )

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingArtifactPolicy]:
        return self._list(
            select(DetectionTrainingArtifactPolicyModel).where(
                DetectionTrainingArtifactPolicyModel.dataset_release_id == dataset_release_id
            )
        )

    def _list(self, statement) -> list[DetectionTrainingArtifactPolicy]:
        statement = statement.order_by(
            DetectionTrainingArtifactPolicyModel.created_at.asc(),
            DetectionTrainingArtifactPolicyModel.id.asc(),
        )
        return [
            detection_training_artifact_policy_to_entity(model)
            for model in self._session.execute(statement).scalars()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
