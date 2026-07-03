from uuid import UUID

from blueberry_microid.application.dto.training_run_comparison_dto import TrainingRunComparisonDTO
from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.training_run_comparison_entry_repository import (
    TrainingRunComparisonEntryRepositoryPort,
)
from blueberry_microid.application.ports.training_run_comparison_repository import (
    TrainingRunComparisonRepositoryPort,
)


class ListTrainingRunComparisonsUseCase:
    def __init__(
        self,
        comparison_repository: TrainingRunComparisonRepositoryPort,
        entry_repository: TrainingRunComparisonEntryRepositoryPort,
        dataset_release_repository: DatasetReleaseRepositoryPort,
    ) -> None:
        self._comparison_repository = comparison_repository
        self._entry_repository = entry_repository
        self._dataset_release_repository = dataset_release_repository

    def execute(self, dataset_release_id: UUID | None = None) -> list[TrainingRunComparisonDTO]:
        if dataset_release_id is not None:
            if self._dataset_release_repository.get_by_id(dataset_release_id) is None:
                raise DatasetReleaseNotFoundError(f"dataset_release '{dataset_release_id}' does not exist")
            comparisons = self._comparison_repository.list_by_dataset_release_id(dataset_release_id)
        else:
            comparisons = self._comparison_repository.list_all()
        return [
            TrainingRunComparisonDTO.from_entity(
                comparison,
                self._entry_repository.list_by_comparison_id(comparison.id),
            )
            for comparison in comparisons
        ]
