from uuid import UUID

from blueberry_microid.application.dto.detection_training_artifact_dto import DetectionTrainingArtifactPolicyDTO
from blueberry_microid.application.exceptions import DetectionTrainingArtifactPolicyNotFoundError
from blueberry_microid.application.ports.detection_training_artifact_policy_repository import (
    DetectionTrainingArtifactPolicyRepositoryPort,
)


class GetDetectionTrainingArtifactPolicyUseCase:
    def __init__(self, policy_repository: DetectionTrainingArtifactPolicyRepositoryPort) -> None:
        self._policy_repository = policy_repository

    def execute(self, artifact_policy_id: UUID) -> DetectionTrainingArtifactPolicyDTO:
        policy = self._policy_repository.get_by_id(artifact_policy_id)
        if policy is None:
            raise DetectionTrainingArtifactPolicyNotFoundError(
                f"detection_training_artifact_policy '{artifact_policy_id}' does not exist"
            )
        return DetectionTrainingArtifactPolicyDTO.from_entity(policy)
