from uuid import UUID

from blueberry_microid.application.dto.training_run_comparison_dto import TrainingRunComparisonEntryDTO
from blueberry_microid.application.exceptions import TrainingRunComparisonNotAllowedError
from blueberry_microid.application.ports.training_run_comparison_entry_repository import (
    TrainingRunComparisonEntryRepositoryPort,
)
from blueberry_microid.application.ports.training_run_comparison_repository import (
    TrainingRunComparisonRepositoryPort,
)


class ListTrainingRunComparisonEntriesUseCase:
    def __init__(
        self,
        comparison_repository: TrainingRunComparisonRepositoryPort,
        entry_repository: TrainingRunComparisonEntryRepositoryPort,
    ) -> None:
        self._comparison_repository = comparison_repository
        self._entry_repository = entry_repository

    def execute(self, comparison_id: UUID) -> list[TrainingRunComparisonEntryDTO]:
        if self._comparison_repository.get_by_id(comparison_id) is None:
            raise TrainingRunComparisonNotAllowedError(f"training_run_comparison '{comparison_id}' does not exist")
        return [
            TrainingRunComparisonEntryDTO.from_entity(entry)
            for entry in self._entry_repository.list_by_comparison_id(comparison_id)
        ]
