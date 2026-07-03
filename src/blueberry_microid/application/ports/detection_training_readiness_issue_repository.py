from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_readiness_issue import (
    DetectionTrainingReadinessIssue,
)


class DetectionTrainingReadinessIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, issues: list[DetectionTrainingReadinessIssue]) -> list[DetectionTrainingReadinessIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_readiness_report_id(self, readiness_report_id: UUID) -> list[DetectionTrainingReadinessIssue]:
        raise NotImplementedError
