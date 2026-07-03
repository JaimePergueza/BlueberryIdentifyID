from uuid import UUID

from blueberry_microid.application.dto.detection_training_environment_dto import (
    DetectionTrainingEnvironmentIssueDTO,
)
from blueberry_microid.application.exceptions import DetectionTrainingEnvironmentSpecNotFoundError
from blueberry_microid.application.ports.detection_training_environment_issue_repository import (
    DetectionTrainingEnvironmentIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_environment_spec_repository import (
    DetectionTrainingEnvironmentSpecRepositoryPort,
)


class ListDetectionTrainingEnvironmentIssuesUseCase:
    def __init__(
        self,
        spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort,
        issue_repository: DetectionTrainingEnvironmentIssueRepositoryPort,
    ) -> None:
        self._spec_repository = spec_repository
        self._issue_repository = issue_repository

    def execute(self, environment_spec_id: UUID) -> list[DetectionTrainingEnvironmentIssueDTO]:
        if self._spec_repository.get_by_id(environment_spec_id) is None:
            raise DetectionTrainingEnvironmentSpecNotFoundError(
                f"detection_training_environment_spec '{environment_spec_id}' does not exist"
            )
        return [
            DetectionTrainingEnvironmentIssueDTO.from_entity(issue)
            for issue in self._issue_repository.list_by_environment_spec_id(environment_spec_id)
        ]
