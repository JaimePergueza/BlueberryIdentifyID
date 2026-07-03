from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.annotation_quality_gate_issue import AnnotationQualityGateIssue


class AnnotationQualityGateIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, issues: list[AnnotationQualityGateIssue]) -> list[AnnotationQualityGateIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_quality_gate_run_id(self, quality_gate_run_id: UUID) -> list[AnnotationQualityGateIssue]:
        raise NotImplementedError
