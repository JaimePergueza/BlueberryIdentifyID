from uuid import UUID

from blueberry_microid.application.dto.annotation_quality_gate_dto import AnnotationQualityGateIssueDTO
from blueberry_microid.application.exceptions import AnnotationQualityGateRunNotFoundError
from blueberry_microid.application.ports.annotation_quality_gate_issue_repository import (
    AnnotationQualityGateIssueRepositoryPort,
)
from blueberry_microid.application.ports.annotation_quality_gate_run_repository import (
    AnnotationQualityGateRunRepositoryPort,
)


class ListAnnotationQualityGateIssuesUseCase:
    def __init__(
        self,
        run_repository: AnnotationQualityGateRunRepositoryPort,
        issue_repository: AnnotationQualityGateIssueRepositoryPort,
    ) -> None:
        self._run_repository = run_repository
        self._issue_repository = issue_repository

    def execute(self, quality_gate_run_id: UUID) -> list[AnnotationQualityGateIssueDTO]:
        if self._run_repository.get_by_id(quality_gate_run_id) is None:
            raise AnnotationQualityGateRunNotFoundError(f"annotation_quality_gate_run '{quality_gate_run_id}' does not exist")
        return [
            AnnotationQualityGateIssueDTO.from_entity(issue)
            for issue in self._issue_repository.list_by_quality_gate_run_id(quality_gate_run_id)
        ]
