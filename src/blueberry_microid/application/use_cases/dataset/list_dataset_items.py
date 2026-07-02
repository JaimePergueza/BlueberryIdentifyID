from uuid import UUID

from blueberry_microid.application.dto.dataset_dto import DatasetItemDTO
from blueberry_microid.application.exceptions import DatasetSnapshotNotFoundError
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort


class ListDatasetItemsUseCase:
    def __init__(
        self,
        dataset_snapshot_repository: DatasetSnapshotRepositoryPort,
        dataset_item_repository: DatasetItemRepositoryPort,
    ) -> None:
        self._dataset_snapshot_repository = dataset_snapshot_repository
        self._dataset_item_repository = dataset_item_repository

    def execute(self, dataset_snapshot_id: UUID) -> list[DatasetItemDTO]:
        if self._dataset_snapshot_repository.get_by_id(dataset_snapshot_id) is None:
            raise DatasetSnapshotNotFoundError(f"dataset_snapshot '{dataset_snapshot_id}' does not exist")
        return [
            DatasetItemDTO.from_entity(item)
            for item in self._dataset_item_repository.list_by_dataset_snapshot_id(dataset_snapshot_id)
        ]

