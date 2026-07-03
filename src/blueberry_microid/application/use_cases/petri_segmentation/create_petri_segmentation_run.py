from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from blueberry_microid.application.dto.petri_segmentation_dto import (
    CreatePetriSegmentationRunRequest,
    PetriSegmentationRunDTO,
    petri_segmentation_config_to_dict,
)
from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError, PetriSegmentationNotAllowedError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.image_dataset_audit_run_repository import (
    ImageDatasetAuditRunRepositoryPort,
)
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.preprocessing.classical_petri_segmenter import ClassicalPetriSegmenter
from blueberry_microid.ml.reports.petri_segmentation_report import PetriCandidateRegionResult


class CreatePetriSegmentationRunUseCase:
    """Run classical Petri-only candidate-region segmentation and persist it.

    No model training, Celery, deep learning, YOLO, taxonomy, or micro-image
    processing happens here.
    """

    def __init__(
        self,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        image_dataset_audit_run_repository: ImageDatasetAuditRunRepositoryPort,
        manifest_exporter: DatasetReleaseManifestExporter,
        segmenter: ClassicalPetriSegmenter,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._dataset_release_repository = dataset_release_repository
        self._image_dataset_audit_run_repository = image_dataset_audit_run_repository
        self._manifest_exporter = manifest_exporter
        self._segmenter = segmenter
        self._unit_of_work = unit_of_work

    def execute(self, request: CreatePetriSegmentationRunRequest) -> PetriSegmentationRunDTO:
        release = self._dataset_release_repository.get_by_id(request.dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{request.dataset_release_id}' does not exist")

        if request.image_audit_run_id is not None:
            audit_run = self._image_dataset_audit_run_repository.get_by_id(request.image_audit_run_id)
            if audit_run is None:
                raise PetriSegmentationNotAllowedError(
                    f"image_audit_run '{request.image_audit_run_id}' does not exist"
                )
            if audit_run.dataset_release_id != request.dataset_release_id:
                raise PetriSegmentationNotAllowedError("image_audit_run does not belong to dataset_release")
            if audit_run.status == ImageDatasetAuditStatus.FAILED:
                raise PetriSegmentationNotAllowedError("failed image_audit_run cannot be used for Petri segmentation")

        manifest = TrainingManifest.from_dict(self._manifest_exporter.export(request.dataset_release_id))
        started_at = datetime.now(timezone.utc)
        report = self._segmenter.segment(manifest, request.config)
        segmentation_run = PetriSegmentationRun(
            dataset_release_id=request.dataset_release_id,
            image_audit_run_id=request.image_audit_run_id,
            status=report.status,
            is_completed=report.is_completed,
            config=petri_segmentation_config_to_dict(request.config),
            total_items=report.total_items,
            processed_petri_images=report.processed_petri_images,
            failed_petri_images=report.failed_petri_images,
            total_regions_detected=report.total_regions_detected,
            mean_regions_per_image=report.mean_regions_per_image,
            summary=report.summary,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            created_by=request.created_by,
            notes=request.notes,
            error_message="; ".join(error.message for error in report.errors) if report.status.value == "failed" else None,
        )
        regions = [
            _region_result_to_entity(result, segmentation_run.id, request.dataset_release_id)
            for result in report.regions
        ]

        with self._unit_of_work as uow:
            created_run = uow.petri_segmentation_run_repository.add(segmentation_run)
            created_regions = uow.petri_segmentation_region_repository.add_many(regions) if regions else []
            uow.commit()

        return PetriSegmentationRunDTO.from_entity(created_run, created_regions)


def _region_result_to_entity(
    result: PetriCandidateRegionResult, segmentation_run_id: UUID, dataset_release_id: UUID
) -> PetriSegmentationRegion:
    return PetriSegmentationRegion(
        segmentation_run_id=segmentation_run_id,
        dataset_release_id=dataset_release_id,
        dataset_item_id=UUID(result.dataset_item_id),
        dataset_split_item_id=UUID(result.dataset_split_item_id),
        split=DatasetSplit(result.split),
        petri_image_path=result.petri_image_path,
        region_index=result.region_index,
        area_px=result.area_px,
        perimeter_px=result.perimeter_px,
        centroid_x=result.centroid_x,
        centroid_y=result.centroid_y,
        bbox_x=result.bbox_x,
        bbox_y=result.bbox_y,
        bbox_width=result.bbox_width,
        bbox_height=result.bbox_height,
        circularity=result.circularity,
        solidity=result.solidity,
        mean_intensity=result.mean_intensity,
        region_features=result.region_features,
    )
