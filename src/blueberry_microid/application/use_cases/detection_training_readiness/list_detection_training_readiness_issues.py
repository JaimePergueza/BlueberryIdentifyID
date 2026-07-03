from uuid import UUID

from blueberry_microid.application.dto.detection_training_readiness_dto import DetectionTrainingReadinessIssueDTO
from blueberry_microid.application.exceptions import DetectionTrainingReadinessReportNotFoundError
from blueberry_microid.application.ports.detection_training_readiness_issue_repository import (
    DetectionTrainingReadinessIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_readiness_report_repository import (
    DetectionTrainingReadinessReportRepositoryPort,
)


class ListDetectionTrainingReadinessIssuesUseCase:
    def __init__(
        self,
        report_repository: DetectionTrainingReadinessReportRepositoryPort,
        issue_repository: DetectionTrainingReadinessIssueRepositoryPort,
    ) -> None:
        self._report_repository = report_repository
        self._issue_repository = issue_repository

    def execute(self, readiness_report_id: UUID) -> list[DetectionTrainingReadinessIssueDTO]:
        if self._report_repository.get_by_id(readiness_report_id) is None:
            raise DetectionTrainingReadinessReportNotFoundError(
                f"detection_training_readiness_report '{readiness_report_id}' does not exist"
            )
        return [
            DetectionTrainingReadinessIssueDTO.from_entity(issue)
            for issue in self._issue_repository.list_by_readiness_report_id(readiness_report_id)
        ]
