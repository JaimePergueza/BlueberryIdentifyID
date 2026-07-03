from uuid import UUID

from blueberry_microid.application.dto.training_run_dto import TrainingRunDTO
from blueberry_microid.application.ports.training_run_repository import TrainingRunRepositoryPort


class ListTrainingRunsUseCase:
    def __init__(self, training_run_repository: TrainingRunRepositoryPort) -> None:
        self._training_run_repository = training_run_repository

    def execute(self, dataset_release_id: UUID | None = None, preflight_run_id: UUID | None = None) -> list[TrainingRunDTO]:
        if dataset_release_id is not None:
            runs = self._training_run_repository.list_by_dataset_release_id(dataset_release_id)
        elif preflight_run_id is not None:
            runs = self._training_run_repository.list_by_preflight_run_id(preflight_run_id)
        else:
            runs = self._training_run_repository.list_all()
        return [TrainingRunDTO.from_entity(run) for run in runs]
