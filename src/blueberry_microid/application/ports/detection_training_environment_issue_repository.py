from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_environment_issue import (
    DetectionTrainingEnvironmentIssue,
)


class DetectionTrainingEnvironmentIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(
        self, issues: list[DetectionTrainingEnvironmentIssue]
    ) -> list[DetectionTrainingEnvironmentIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_environment_spec_id(self, environment_spec_id: UUID) -> list[DetectionTrainingEnvironmentIssue]:
        raise NotImplementedError
