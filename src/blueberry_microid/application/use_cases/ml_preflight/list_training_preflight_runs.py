from uuid import UUID

from blueberry_microid.application.dto.ml_preflight_dto import TrainingPreflightRunDTO
from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.training_preflight_run_repository import TrainingPreflightRunRepositoryPort


class ListTrainingPreflightRunsUseCase:
    def __init__(
        self,
        preflight_run_repository: TrainingPreflightRunRepositoryPort,
        dataset_release_repository: DatasetReleaseRepositoryPort | None = None,
    ) -> None:
        self._preflight_run_repository = preflight_run_repository
        self._dataset_release_repository = dataset_release_repository

    def execute(self, dataset_release_id: UUID | None = None) -> list[TrainingPreflightRunDTO]:
        if dataset_release_id is None:
            runs = self._preflight_run_repository.list_all()
        else:
            if self._dataset_release_repository is not None:
                release = self._dataset_release_repository.get_by_id(dataset_release_id)
                if release is None:
                    raise DatasetReleaseNotFoundError(f"dataset_release '{dataset_release_id}' does not exist")
            runs = self._preflight_run_repository.list_by_dataset_release_id(dataset_release_id)
        return [TrainingPreflightRunDTO.from_entity(run) for run in runs]
