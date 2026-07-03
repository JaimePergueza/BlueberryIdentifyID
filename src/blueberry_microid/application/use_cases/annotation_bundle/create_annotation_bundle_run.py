from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from blueberry_microid.application.dto.annotation_bundle_dto import (
    AnnotationBundleRunDTO,
    CreateAnnotationBundleRunRequest,
)
from blueberry_microid.application.exceptions import (
    AnnotationBundleNotAllowedError,
    PetriAnnotationExportRunNotFoundError,
)
from blueberry_microid.application.ports.petri_annotation_export_item_repository import (
    PetriAnnotationExportItemRepositoryPort,
)
from blueberry_microid.application.ports.petri_annotation_export_run_repository import (
    PetriAnnotationExportRunRepositoryPort,
)
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.annotation_bundle_validator import AnnotationBundleValidator
from blueberry_microid.application.services.annotation_bundle_writer import AnnotationBundleWriter
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus


class CreateAnnotationBundleRunUseCase:
    def __init__(
        self,
        export_run_repository: PetriAnnotationExportRunRepositoryPort,
        export_item_repository: PetriAnnotationExportItemRepositoryPort,
        validator: AnnotationBundleValidator,
        writer: AnnotationBundleWriter,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._export_run_repository = export_run_repository
        self._export_item_repository = export_item_repository
        self._validator = validator
        self._writer = writer
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateAnnotationBundleRunRequest) -> AnnotationBundleRunDTO:
        export_run = self._export_run_repository.get_by_id(request.petri_annotation_export_run_id)
        if export_run is None:
            raise PetriAnnotationExportRunNotFoundError(
                f"petri_annotation_export_run '{request.petri_annotation_export_run_id}' does not exist"
            )
        try:
            config = request.config.to_config()
        except ValueError as exc:
            raise AnnotationBundleNotAllowedError(str(exc)) from exc
        items = self._export_item_repository.list_by_export_run_id(export_run.id)
        validation = self._validator.validate(export_run, items, config)
        if config.validate_before_write and not validation.is_valid and config.fail_on_invalid_bbox:
            raise AnnotationBundleNotAllowedError("; ".join(validation.errors))

        bundle_run_id = uuid4()
        try:
            write_result = self._writer.write(
                bundle_run_id=bundle_run_id,
                export_run=export_run,
                items=items,
                config=config,
                validation_report=validation,
            )
        except ValueError as exc:
            raise AnnotationBundleNotAllowedError(str(exc)) from exc
        status = AnnotationBundleStatus.DRY_RUN if config.dry_run else AnnotationBundleStatus.COMPLETED
        now = datetime.now(timezone.utc)
        bundle_run = AnnotationBundleRun(
            id=bundle_run_id,
            petri_annotation_export_run_id=export_run.id,
            dataset_release_id=export_run.dataset_release_id,
            petri_segmentation_run_id=export_run.petri_segmentation_run_id,
            status=status,
            is_completed=True,
            config=config.to_dict(),
            output_dir=config.output_dir,
            dry_run=config.dry_run,
            file_count=len(write_result.files),
            annotation_count=len(items),
            image_count=len({item.petri_image_path for item in items}),
            label_count=len([file for file in write_result.files if file.file_role.value == "yolo_label"]),
            validation_summary=validation.to_dict(),
            bundle_manifest=write_result.bundle_manifest,
            completed_at=now,
            created_by=request.created_by,
            notes=request.notes,
        )

        with self._unit_of_work as uow:
            created = uow.annotation_bundle_run_repository.add(bundle_run)
            if write_result.files:
                uow.annotation_bundle_file_repository.add_many(write_result.files)
            uow.commit()
        return AnnotationBundleRunDTO.from_entity(created)
