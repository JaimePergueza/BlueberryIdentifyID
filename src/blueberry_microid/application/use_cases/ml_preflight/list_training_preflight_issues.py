from uuid import UUID

from blueberry_microid.application.dto.ml_preflight_dto import TrainingPreflightIssueDTO
from blueberry_microid.application.exceptions import TrainingPreflightRunNotFoundError
from blueberry_microid.application.ports.training_preflight_issue_repository import TrainingPreflightIssueRepositoryPort
from blueberry_microid.application.ports.training_preflight_run_repository import TrainingPreflightRunRepositoryPort


class ListTrainingPreflightIssuesUseCase:
    def __init__(
        self,
        preflight_run_repository: TrainingPreflightRunRepositoryPort,
        preflight_issue_repository: TrainingPreflightIssueRepositoryPort,
    ) -> None:
        self._preflight_run_repository = preflight_run_repository
        self._preflight_issue_repository = preflight_issue_repository

    def execute(self, preflight_run_id: UUID) -> list[TrainingPreflightIssueDTO]:
        preflight_run = self._preflight_run_repository.get_by_id(preflight_run_id)
        if preflight_run is None:
            raise TrainingPreflightRunNotFoundError(f"training_preflight_run '{preflight_run_id}' does not exist")
        issues = self._preflight_issue_repository.list_by_preflight_run_id(preflight_run_id)
        return [TrainingPreflightIssueDTO.from_entity(issue) for issue in issues]
