from uuid import UUID

from blueberry_microid.application.dto.image_feature_extraction_dto import ImageFeatureExtractionRunDTO
from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError, ImageDatasetAuditRunNotFoundError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.image_dataset_audit_run_repository import (
    ImageDatasetAuditRunRepositoryPort,
)
from blueberry_microid.application.ports.image_feature_extraction_run_repository import (
    ImageFeatureExtractionRunRepositoryPort,
)


class ListImageFeatureExtractionRunsUseCase:
    def __init__(
        self,
        extraction_run_repository: ImageFeatureExtractionRunRepositoryPort,
        dataset_release_repository: DatasetReleaseRepositoryPort | None = None,
        image_dataset_audit_run_repository: ImageDatasetAuditRunRepositoryPort | None = None,
    ) -> None:
        self._extraction_run_repository = extraction_run_repository
        self._dataset_release_repository = dataset_release_repository
        self._image_dataset_audit_run_repository = image_dataset_audit_run_repository

    def execute(
        self,
        dataset_release_id: UUID | None = None,
        image_audit_run_id: UUID | None = None,
    ) -> list[ImageFeatureExtractionRunDTO]:
        if dataset_release_id is not None:
            if self._dataset_release_repository is not None:
                release = self._dataset_release_repository.get_by_id(dataset_release_id)
                if release is None:
                    raise DatasetReleaseNotFoundError(f"dataset_release '{dataset_release_id}' does not exist")
            runs = self._extraction_run_repository.list_by_dataset_release_id(dataset_release_id)
        elif image_audit_run_id is not None:
            if self._image_dataset_audit_run_repository is not None:
                audit_run = self._image_dataset_audit_run_repository.get_by_id(image_audit_run_id)
                if audit_run is None:
                    raise ImageDatasetAuditRunNotFoundError(
                        f"image_dataset_audit_run '{image_audit_run_id}' does not exist"
                    )
            runs = self._extraction_run_repository.list_by_image_audit_run_id(image_audit_run_id)
        else:
            runs = self._extraction_run_repository.list_all()
        return [ImageFeatureExtractionRunDTO.from_entity(run) for run in runs]
