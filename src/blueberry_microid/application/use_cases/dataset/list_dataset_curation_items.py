from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.dataset_curation_dto import DatasetCurationItemDTO
from blueberry_microid.application.exceptions import DatasetCurationRunNotFoundError
from blueberry_microid.application.ports.dataset_curation_repository import (
    DatasetCurationItemRepositoryPort,
    DatasetCurationRunRepositoryPort,
)
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus


class ListDatasetCurationItemsUseCase:
    def __init__(
        self,
        run_repository: DatasetCurationRunRepositoryPort,
        item_repository: DatasetCurationItemRepositoryPort,
    ) -> None:
        self._run_repository = run_repository
        self._item_repository = item_repository

    def execute(
        self,
        curation_run_id: UUID,
        *,
        status: Optional[DatasetCurationStatus] = None,
    ) -> list[DatasetCurationItemDTO]:
        if self._run_repository.get_by_id(curation_run_id) is None:
            raise DatasetCurationRunNotFoundError(f"dataset curation run '{curation_run_id}' was not found")
        return [
            DatasetCurationItemDTO.from_entity(item)
            for item in self._item_repository.list_by_curation_run_id(curation_run_id, status=status)
        ]

