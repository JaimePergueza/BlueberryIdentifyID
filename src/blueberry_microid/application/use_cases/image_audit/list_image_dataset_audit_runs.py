from uuid import UUID

from blueberry_microid.application.dto.image_audit_dto import ImageDatasetAuditRunDTO
from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.image_dataset_audit_run_repository import (
    ImageDatasetAuditRunRepositoryPort,
)


class ListImageDatasetAuditRunsUseCase:
    def __init__(
        self,
        audit_run_repository: ImageDatasetAuditRunRepositoryPort,
        dataset_release_repository: DatasetReleaseRepositoryPort | None = None,
    ) -> None:
        self._audit_run_repository = audit_run_repository
        self._dataset_release_repository = dataset_release_repository

    def execute(self, dataset_release_id: UUID | None = None) -> list[ImageDatasetAuditRunDTO]:
        if dataset_release_id is None:
            runs = self._audit_run_repository.list_all()
        else:
            if self._dataset_release_repository is not None:
                release = self._dataset_release_repository.get_by_id(dataset_release_id)
                if release is None:
                    raise DatasetReleaseNotFoundError(f"dataset_release '{dataset_release_id}' does not exist")
            runs = self._audit_run_repository.list_by_dataset_release_id(dataset_release_id)
        return [ImageDatasetAuditRunDTO.from_entity(run) for run in runs]
