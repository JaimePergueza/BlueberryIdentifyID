from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from blueberry_microid.application.dto.petri_annotation_export_dto import (
    CreatePetriAnnotationExportRunRequest,
    PetriAnnotationExportRunDTO,
)
from blueberry_microid.application.exceptions import (
    DatasetReleaseNotFoundError,
    PetriAnnotationExportNotAllowedError,
    PetriSegmentationRunNotFoundError,
)
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.application.ports.petri_segmentation_run_repository import PetriSegmentationRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.petri_annotation_exporter import PetriAnnotationExporter
from blueberry_microid.domain.entities.petri_annotation_export_run import PetriAnnotationExportRun
from blueberry_microid.domain.enums.petri_annotation_export_status import PetriAnnotationExportStatus


class CreatePetriAnnotationExportRunUseCase:
    def __init__(
        self,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        segmentation_run_repository: PetriSegmentationRunRepositoryPort,
        region_repository: PetriSegmentationRegionRepositoryPort,
        review_repository: PetriRegionReviewRepositoryPort,
        exporter: PetriAnnotationExporter,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._dataset_release_repository = dataset_release_repository
        self._segmentation_run_repository = segmentation_run_repository
        self._region_repository = region_repository
        self._review_repository = review_repository
        self._exporter = exporter
        self._unit_of_work = unit_of_work

    def execute(self, request: CreatePetriAnnotationExportRunRequest) -> PetriAnnotationExportRunDTO:
        release = self._dataset_release_repository.get_by_id(request.dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{request.dataset_release_id}' does not exist")

        segmentation_run = self._segmentation_run_repository.get_by_id(request.petri_segmentation_run_id)
        if segmentation_run is None:
            raise PetriSegmentationRunNotFoundError(
                f"petri_segmentation_run '{request.petri_segmentation_run_id}' does not exist"
            )
        if segmentation_run.dataset_release_id != release.id:
            raise PetriAnnotationExportNotAllowedError(
                "petri_segmentation_run does not belong to the requested dataset_release"
            )

        config = request.config.to_config()
        regions = self._region_repository.list_by_segmentation_run_id(segmentation_run.id)
        reviews = self._review_repository.list_by_segmentation_run_id(segmentation_run.id)
        export_run_id = uuid4()
        result = self._exporter.export(
            segmentation_run=segmentation_run,
            regions=regions,
            reviews=reviews,
            config=config,
            export_run_id=export_run_id,
        )

        status = PetriAnnotationExportStatus.FAILED if result.errors else PetriAnnotationExportStatus.COMPLETED
        if result.warnings and not result.errors:
            status = PetriAnnotationExportStatus.PARTIAL
        now = datetime.now(timezone.utc)
        output_manifest = result.output_manifest if not result.errors else {"errors": result.errors}
        export_run = PetriAnnotationExportRun(
            id=export_run_id,
            dataset_release_id=release.id,
            petri_segmentation_run_id=segmentation_run.id,
            export_format=config.export_format,
            status=status,
            is_completed=status != PetriAnnotationExportStatus.FAILED,
            config=config.to_dict(),
            exported_annotation_count=len(result.items),
            skipped_review_count=result.summary["skipped_review_count"],
            image_count=len({item.petri_image_path for item in result.items}),
            category_count=1,
            output_manifest=output_manifest,
            summary=result.summary,
            completed_at=now if status != PetriAnnotationExportStatus.FAILED else None,
            created_by=request.created_by,
            notes=request.notes,
            error_message="; ".join(result.errors) if result.errors else None,
        )

        with self._unit_of_work as uow:
            created = uow.petri_annotation_export_run_repository.add(export_run)
            if result.items:
                uow.petri_annotation_export_item_repository.add_many(result.items)
            uow.commit()
        return PetriAnnotationExportRunDTO.from_entity(created)
