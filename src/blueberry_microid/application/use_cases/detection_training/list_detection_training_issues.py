from uuid import UUID

from blueberry_microid.application.dto.detection_training_dto import DetectionTrainingIssueDTO
from blueberry_microid.application.exceptions import DetectionTrainingRunNotFoundError
from blueberry_microid.application.ports.detection_training_issue_repository import (
    DetectionTrainingIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort


class ListDetectionTrainingIssuesUseCase:
    def __init__(
        self,
        run_repository: DetectionTrainingRunRepositoryPort,
        issue_repository: DetectionTrainingIssueRepositoryPort,
    ) -> None:
        self._run_repository = run_repository
        self._issue_repository = issue_repository

    def execute(self, detection_training_run_id: UUID) -> list[DetectionTrainingIssueDTO]:
        if self._run_repository.get_by_id(detection_training_run_id) is None:
            raise DetectionTrainingRunNotFoundError(
                f"detection_training_run '{detection_training_run_id}' does not exist"
            )
        return [
            DetectionTrainingIssueDTO.from_entity(issue)
            for issue in self._issue_repository.list_by_detection_training_run_id(detection_training_run_id)
        ]
