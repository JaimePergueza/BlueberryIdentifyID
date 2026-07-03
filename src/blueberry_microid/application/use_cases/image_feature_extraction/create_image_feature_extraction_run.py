from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from blueberry_microid.application.dto.image_feature_extraction_dto import (
    CreateImageFeatureExtractionRunRequest,
    ImageFeatureExtractionRunDTO,
    image_feature_extraction_config_to_dict,
)
from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError, ImageFeatureExtractionNotAllowedError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.image_dataset_audit_run_repository import (
    ImageDatasetAuditRunRepositoryPort,
)
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.domain.entities.image_feature_extraction_run import ImageFeatureExtractionRun
from blueberry_microid.domain.entities.image_feature_vector import ImageFeatureVector
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.preprocessing.image_feature_extractor import EXTRACTION_VERSION, ImageFeatureExtractor
from blueberry_microid.ml.reports.image_feature_extraction_report import FeatureVectorResult


class CreateImageFeatureExtractionRunUseCase:
    """Extract simple, non-deep, reproducible features from the Petri/micro
    images referenced by a DatasetRelease whose ImageDatasetAuditRun was not
    failed, and persist the run + per-image vectors transactionally.

    No model training, PyTorch, TensorFlow, or Celery happens here — this
    reuses the existing manifest exporter (same pattern as the Fase 12
    preflight and Fase 14 image audit) and a Pillow/numpy-based extractor.
    """

    def __init__(
        self,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        image_dataset_audit_run_repository: ImageDatasetAuditRunRepositoryPort,
        manifest_exporter: DatasetReleaseManifestExporter,
        image_feature_extractor: ImageFeatureExtractor,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._dataset_release_repository = dataset_release_repository
        self._image_dataset_audit_run_repository = image_dataset_audit_run_repository
        self._manifest_exporter = manifest_exporter
        self._image_feature_extractor = image_feature_extractor
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateImageFeatureExtractionRunRequest) -> ImageFeatureExtractionRunDTO:
        release = self._dataset_release_repository.get_by_id(request.dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{request.dataset_release_id}' does not exist")

        audit_run = self._image_dataset_audit_run_repository.get_by_id(request.image_audit_run_id)
        if audit_run is None:
            raise ImageFeatureExtractionNotAllowedError(
                f"image_audit_run '{request.image_audit_run_id}' does not exist"
            )
        if audit_run.dataset_release_id != request.dataset_release_id:
            raise ImageFeatureExtractionNotAllowedError("image_audit_run does not belong to dataset_release")

        acceptable_statuses: set[ImageDatasetAuditStatus] = set()
        if request.config.require_audit_passed:
            acceptable_statuses.add(ImageDatasetAuditStatus.PASSED)
        if request.config.allow_audit_warning:
            acceptable_statuses.add(ImageDatasetAuditStatus.WARNING)
        if audit_run.status not in acceptable_statuses:
            raise ImageFeatureExtractionNotAllowedError(
                f"image_audit_run status '{audit_run.status.value}' is not acceptable for feature extraction"
            )

        manifest = TrainingManifest.from_dict(self._manifest_exporter.export(request.dataset_release_id))
        started_at = datetime.now(timezone.utc)
        report = self._image_feature_extractor.extract(manifest, request.config)

        extraction_run = ImageFeatureExtractionRun(
            dataset_release_id=request.dataset_release_id,
            image_audit_run_id=request.image_audit_run_id,
            status=report.status,
            is_completed=report.is_completed,
            config=image_feature_extraction_config_to_dict(request.config),
            total_items=report.total_items,
            processed_items=report.processed_items,
            failed_items=report.failed_items,
            total_feature_vectors=report.total_feature_vectors,
            petri_feature_count=report.petri_feature_count,
            micro_feature_count=report.micro_feature_count,
            summary=report.summary,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            created_by=request.created_by,
            notes=request.notes,
        )

        vectors = [
            _vector_result_to_entity(result, extraction_run.id, request.dataset_release_id)
            for result in report.vectors
        ]

        with self._unit_of_work as uow:
            created_run = uow.image_feature_extraction_run_repository.add(extraction_run)
            created_vectors = uow.image_feature_vector_repository.add_many(vectors) if vectors else []
            uow.commit()

        return ImageFeatureExtractionRunDTO.from_entity(created_run, created_vectors)


def _vector_result_to_entity(
    result: FeatureVectorResult, feature_extraction_run_id: UUID, dataset_release_id: UUID
) -> ImageFeatureVector:
    return ImageFeatureVector(
        feature_extraction_run_id=feature_extraction_run_id,
        dataset_release_id=dataset_release_id,
        dataset_item_id=UUID(result.dataset_item_id),
        dataset_split_item_id=UUID(result.dataset_split_item_id),
        split=DatasetSplit(result.split),
        modality=result.modality,
        image_path=result.image_path,
        features=result.features,
        preprocessing=result.preprocessing,
        extraction_version=EXTRACTION_VERSION,
    )
