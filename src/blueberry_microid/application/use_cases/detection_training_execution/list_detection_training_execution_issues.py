from uuid import UUID

from blueberry_microid.application.dto.detection_training_execution_dto import DetectionTrainingExecutionIssueDTO
from blueberry_microid.application.exceptions import DetectionTrainingExecutionRunNotFoundError
from blueberry_microid.application.ports.detection_training_execution_issue_repository import (
    DetectionTrainingExecutionIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_execution_run_repository import (
    DetectionTrainingExecutionRunRepositoryPort,
)


class ListDetectionTrainingExecutionIssuesUseCase:
    def __init__(
        self,
        execution_run_repository: DetectionTrainingExecutionRunRepositoryPort,
        execution_issue_repository: DetectionTrainingExecutionIssueRepositoryPort,
    ) -> None:
        self._execution_run_repository = execution_run_repository
        self._execution_issue_repository = execution_issue_repository

    def execute(self, execution_run_id: UUID) -> list[DetectionTrainingExecutionIssueDTO]:
        if self._execution_run_repository.get_by_id(execution_run_id) is None:
            raise DetectionTrainingExecutionRunNotFoundError(
                f"detection_training_execution_run '{execution_run_id}' does not exist"
            )
        return [
            DetectionTrainingExecutionIssueDTO.from_entity(issue)
            for issue in self._execution_issue_repository.list_by_execution_run_id(execution_run_id)
        ]
