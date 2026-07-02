from uuid import UUID

from blueberry_microid.application.dto.dataset_dto import DatasetSnapshotDTO
from blueberry_microid.application.exceptions import DatasetSnapshotNotFoundError
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort


class GetDatasetSnapshotUseCase:
    def __init__(self, dataset_snapshot_repository: DatasetSnapshotRepositoryPort) -> None:
        self._dataset_snapshot_repository = dataset_snapshot_repository

    def execute(self, dataset_snapshot_id: UUID) -> DatasetSnapshotDTO:
        snapshot = self._dataset_snapshot_repository.get_by_id(dataset_snapshot_id)
        if snapshot is None:
            raise DatasetSnapshotNotFoundError(f"dataset_snapshot '{dataset_snapshot_id}' does not exist")
        return DatasetSnapshotDTO.from_entity(snapshot)

