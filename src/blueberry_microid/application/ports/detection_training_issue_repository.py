from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_issue import DetectionTrainingIssue


class DetectionTrainingIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, issues: list[DetectionTrainingIssue]) -> list[DetectionTrainingIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_detection_training_run_id(self, detection_training_run_id: UUID) -> list[DetectionTrainingIssue]:
        raise NotImplementedError
