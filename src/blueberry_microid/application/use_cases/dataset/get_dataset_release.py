from uuid import UUID

from blueberry_microid.application.dto.dataset_dto import DatasetReleaseDTO
from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort


class GetDatasetReleaseUseCase:
    def __init__(self, dataset_release_repository: DatasetReleaseRepositoryPort) -> None:
        self._dataset_release_repository = dataset_release_repository

    def execute(self, dataset_release_id: UUID) -> DatasetReleaseDTO:
        release = self._dataset_release_repository.get_by_id(dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{dataset_release_id}' does not exist")
        return DatasetReleaseDTO.from_entity(release)
