from uuid import UUID

from blueberry_microid.application.dto.dataset_dto import DatasetSplitItemDTO
from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.dataset_split_item_repository import DatasetSplitItemRepositoryPort


class ListDatasetSplitItemsUseCase:
    def __init__(
        self,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        dataset_split_item_repository: DatasetSplitItemRepositoryPort,
    ) -> None:
        self._dataset_release_repository = dataset_release_repository
        self._dataset_split_item_repository = dataset_split_item_repository

    def execute(self, dataset_release_id: UUID) -> list[DatasetSplitItemDTO]:
        release = self._dataset_release_repository.get_by_id(dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{dataset_release_id}' does not exist")
        items = self._dataset_split_item_repository.list_by_dataset_release_id(dataset_release_id)
        return [DatasetSplitItemDTO.from_entity(item) for item in items]
