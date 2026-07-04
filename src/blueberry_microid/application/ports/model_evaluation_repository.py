from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.model_candidate import ModelCandidate
from blueberry_microid.domain.entities.model_evaluation_issue import ModelEvaluationIssue
from blueberry_microid.domain.entities.model_evaluation_run import ModelEvaluationRun
from blueberry_microid.domain.entities.model_promotion_gate_run import ModelPromotionGateRun


class ModelCandidateRepositoryPort(ABC):
    @abstractmethod
    def add(self, candidate: ModelCandidate) -> ModelCandidate:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, candidate_id: UUID) -> ModelCandidate | None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[ModelCandidate]:
        raise NotImplementedError


class ModelEvaluationRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, run: ModelEvaluationRun) -> ModelEvaluationRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, run_id: UUID) -> ModelEvaluationRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_model_candidate_id(self, candidate_id: UUID) -> list[ModelEvaluationRun]:
        raise NotImplementedError


class ModelEvaluationIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, issues: list[ModelEvaluationIssue]) -> list[ModelEvaluationIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_model_evaluation_run_id(self, run_id: UUID) -> list[ModelEvaluationIssue]:
        raise NotImplementedError


class ModelPromotionGateRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, run: ModelPromotionGateRun) -> ModelPromotionGateRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, run_id: UUID) -> ModelPromotionGateRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_model_candidate_id(self, candidate_id: UUID) -> list[ModelPromotionGateRun]:
        raise NotImplementedError
