from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.detection_training_artifact_dto import DetectionTrainingArtifactPolicyDTO
from blueberry_microid.application.ports.detection_training_artifact_policy_repository import (
    DetectionTrainingArtifactPolicyRepositoryPort,
)


class ListDetectionTrainingArtifactPoliciesUseCase:
    def __init__(self, policy_repository: DetectionTrainingArtifactPolicyRepositoryPort) -> None:
        self._policy_repository = policy_repository

    def execute(
        self,
        *,
        detection_training_run_id: Optional[UUID] = None,
        readiness_report_id: Optional[UUID] = None,
        environment_spec_id: Optional[UUID] = None,
        annotation_bundle_run_id: Optional[UUID] = None,
        dataset_release_id: Optional[UUID] = None,
    ) -> list[DetectionTrainingArtifactPolicyDTO]:
        if detection_training_run_id is not None:
            policies = self._policy_repository.list_by_detection_training_run_id(detection_training_run_id)
        elif readiness_report_id is not None:
            policies = self._policy_repository.list_by_readiness_report_id(readiness_report_id)
        elif environment_spec_id is not None:
            policies = self._policy_repository.list_by_environment_spec_id(environment_spec_id)
        elif annotation_bundle_run_id is not None:
            policies = self._policy_repository.list_by_annotation_bundle_run_id(annotation_bundle_run_id)
        elif dataset_release_id is not None:
            policies = self._policy_repository.list_by_dataset_release_id(dataset_release_id)
        else:
            policies = self._policy_repository.list_all()
        return [DetectionTrainingArtifactPolicyDTO.from_entity(policy) for policy in policies]
