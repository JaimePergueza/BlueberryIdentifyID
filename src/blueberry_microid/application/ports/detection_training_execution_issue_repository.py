from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_execution_issue import DetectionTrainingExecutionIssue


class DetectionTrainingExecutionIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, issues: list[DetectionTrainingExecutionIssue]) -> list[DetectionTrainingExecutionIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_execution_run_id(self, execution_run_id: UUID) -> list[DetectionTrainingExecutionIssue]:
        raise NotImplementedError
