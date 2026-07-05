from uuid import UUID

from blueberry_microid.application.dto.dataset_curation_dto import DatasetCurationRunDTO
from blueberry_microid.application.exceptions import DatasetCurationRunNotFoundError
from blueberry_microid.application.ports.dataset_curation_repository import DatasetCurationRunRepositoryPort


class GetDatasetCurationRunUseCase:
    def __init__(self, repository: DatasetCurationRunRepositoryPort) -> None:
        self._repository = repository

    def execute(self, curation_run_id: UUID) -> DatasetCurationRunDTO:
        run = self._repository.get_by_id(curation_run_id)
        if run is None:
            raise DatasetCurationRunNotFoundError(f"dataset curation run '{curation_run_id}' was not found")
        return DatasetCurationRunDTO.from_entity(run)

