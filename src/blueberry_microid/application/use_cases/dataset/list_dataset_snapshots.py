from blueberry_microid.application.dto.dataset_dto import DatasetSnapshotDTO
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort


class ListDatasetSnapshotsUseCase:
    def __init__(self, dataset_snapshot_repository: DatasetSnapshotRepositoryPort) -> None:
        self._dataset_snapshot_repository = dataset_snapshot_repository

    def execute(self) -> list[DatasetSnapshotDTO]:
        return [DatasetSnapshotDTO.from_entity(snapshot) for snapshot in self._dataset_snapshot_repository.list_all()]

