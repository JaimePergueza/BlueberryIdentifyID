from uuid import UUID

from blueberry_microid.application.dto.detection_training_artifact_dto import DetectionTrainingArtifactIssueDTO
from blueberry_microid.application.exceptions import DetectionTrainingArtifactPolicyNotFoundError
from blueberry_microid.application.ports.detection_training_artifact_issue_repository import (
    DetectionTrainingArtifactIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_artifact_policy_repository import (
    DetectionTrainingArtifactPolicyRepositoryPort,
)


class ListDetectionTrainingArtifactIssuesUseCase:
    def __init__(
        self,
        policy_repository: DetectionTrainingArtifactPolicyRepositoryPort,
        issue_repository: DetectionTrainingArtifactIssueRepositoryPort,
    ) -> None:
        self._policy_repository = policy_repository
        self._issue_repository = issue_repository

    def execute(self, artifact_policy_id: UUID) -> list[DetectionTrainingArtifactIssueDTO]:
        if self._policy_repository.get_by_id(artifact_policy_id) is None:
            raise DetectionTrainingArtifactPolicyNotFoundError(
                f"detection_training_artifact_policy '{artifact_policy_id}' does not exist"
            )
        return [
            DetectionTrainingArtifactIssueDTO.from_entity(issue)
            for issue in self._issue_repository.list_by_artifact_policy_id(artifact_policy_id)
        ]
