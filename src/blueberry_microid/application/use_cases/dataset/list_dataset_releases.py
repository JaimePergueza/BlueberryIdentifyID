from blueberry_microid.application.dto.dataset_dto import DatasetReleaseDTO
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort


class ListDatasetReleasesUseCase:
    def __init__(self, dataset_release_repository: DatasetReleaseRepositoryPort) -> None:
        self._dataset_release_repository = dataset_release_repository

    def execute(self) -> list[DatasetReleaseDTO]:
        return [DatasetReleaseDTO.from_entity(release) for release in self._dataset_release_repository.list_all()]
