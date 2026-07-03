from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.training_preflight_issue import TrainingPreflightIssue


class TrainingPreflightIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, issues: list[TrainingPreflightIssue]) -> list[TrainingPreflightIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_preflight_run_id(self, preflight_run_id: UUID) -> list[TrainingPreflightIssue]:
        raise NotImplementedError
