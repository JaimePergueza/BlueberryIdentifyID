from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_artifact_issue import DetectionTrainingArtifactIssue


class DetectionTrainingArtifactIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, issues: list[DetectionTrainingArtifactIssue]) -> list[DetectionTrainingArtifactIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_artifact_policy_id(self, artifact_policy_id: UUID) -> list[DetectionTrainingArtifactIssue]:
        raise NotImplementedError
