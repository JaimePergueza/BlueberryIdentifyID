from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from blueberry_microid.application.dto.detection_training_dto import (
    CreateDetectionTrainingRunRequest,
    DetectionTrainingRunDTO,
)
from blueberry_microid.application.exceptions import (
    AnnotationBundleRunNotFoundError,
    AnnotationQualityGateRunNotFoundError,
    DetectionTrainingNotAllowedError,
)
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort
from blueberry_microid.application.ports.annotation_quality_gate_run_repository import (
    AnnotationQualityGateRunRepositoryPort,
)
from blueberry_microid.application.ports.object_detection_trainer import ObjectDetectionTrainerPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.domain.entities.detection_training_issue import DetectionTrainingIssue
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus


class CreateDetectionTrainingRunUseCase:
    """Plans a detection training dry-run; never trains a model.

    Never modifies the referenced AnnotationBundleRun or
    AnnotationQualityGateRun, never touches image files, and never runs a
    training command.
    """

    def __init__(
        self,
        bundle_run_repository: AnnotationBundleRunRepositoryPort,
        bundle_file_repository: AnnotationBundleFileRepositoryPort,
        quality_gate_run_repository: AnnotationQualityGateRunRepositoryPort,
        trainer: ObjectDetectionTrainerPort,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._bundle_run_repository = bundle_run_repository
        self._bundle_file_repository = bundle_file_repository
        self._quality_gate_run_repository = quality_gate_run_repository
        self._trainer = trainer
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateDetectionTrainingRunRequest) -> DetectionTrainingRunDTO:
        bundle_run = self._bundle_run_repository.get_by_id(request.annotation_bundle_run_id)
        if bundle_run is None:
            raise AnnotationBundleRunNotFoundError(
                f"annotation_bundle_run '{request.annotation_bundle_run_id}' does not exist"
            )

        quality_gate_run = self._quality_gate_run_repository.get_by_id(request.annotation_quality_gate_run_id)
        if quality_gate_run is None:
            raise AnnotationQualityGateRunNotFoundError(
                f"annotation_quality_gate_run '{request.annotation_quality_gate_run_id}' does not exist"
            )
        if quality_gate_run.annotation_bundle_run_id != bundle_run.id:
            raise DetectionTrainingNotAllowedError(
                f"annotation_quality_gate_run '{quality_gate_run.id}' does not belong to "
                f"annotation_bundle_run '{bundle_run.id}'"
            )

        try:
            config = request.config.to_config()
        except ValueError as exc:
            raise DetectionTrainingNotAllowedError(str(exc)) from exc

        bundle_files = self._bundle_file_repository.list_by_bundle_run_id(bundle_run.id)

        now = datetime.now(timezone.utc)
        run_id = uuid4()
        try:
            plan = self._trainer.plan_training(bundle_run, bundle_files, quality_gate_run, config)
            error_count = sum(1 for issue in plan.issues if issue.severity.value == "error")
            warning_count = sum(1 for issue in plan.issues if issue.severity.value == "warning")
            run = DetectionTrainingRun(
                id=run_id,
                annotation_bundle_run_id=bundle_run.id,
                annotation_quality_gate_run_id=quality_gate_run.id,
                dataset_release_id=bundle_run.dataset_release_id,
                petri_annotation_export_run_id=bundle_run.petri_annotation_export_run_id,
                algorithm=config.algorithm,
                mode=config.mode,
                status=plan.status,
                is_runnable=plan.is_runnable,
                config=config.to_dict(),
                training_plan=plan.training_plan,
                command_preview=plan.command_preview,
                dataset_summary=plan.dataset_summary,
                quality_gate_summary=plan.quality_gate_summary,
                expected_outputs=plan.expected_outputs,
                issue_count=len(plan.issues),
                warning_count=warning_count,
                error_count=error_count,
                completed_at=now,
                created_by=request.created_by,
                notes=request.notes,
                error_message="; ".join(
                    issue.message for issue in plan.issues if issue.severity.value == "error"
                )[:2000]
                or None,
            )
            issues = [
                DetectionTrainingIssue(
                    id=issue.id,
                    detection_training_run_id=run_id,
                    severity=issue.severity,
                    code=issue.code,
                    message=issue.message,
                    details=issue.details,
                    created_at=issue.created_at,
                )
                for issue in plan.issues
            ]
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any planning failure becomes a failed run
            run = DetectionTrainingRun(
                id=run_id,
                annotation_bundle_run_id=bundle_run.id,
                annotation_quality_gate_run_id=quality_gate_run.id,
                dataset_release_id=bundle_run.dataset_release_id,
                petri_annotation_export_run_id=bundle_run.petri_annotation_export_run_id,
                algorithm=config.algorithm,
                mode=config.mode,
                status=DetectionTrainingStatus.FAILED,
                is_runnable=False,
                config=config.to_dict(),
                training_plan={},
                command_preview={},
                dataset_summary={},
                quality_gate_summary={},
                expected_outputs={},
                issue_count=0,
                warning_count=0,
                error_count=0,
                completed_at=now,
                created_by=request.created_by,
                notes=request.notes,
                error_message=str(exc)[:2000],
            )
            issues = []

        with self._unit_of_work as uow:
            created = uow.detection_training_run_repository.add(run)
            if issues:
                uow.detection_training_issue_repository.add_many(issues)
            uow.commit()
        return DetectionTrainingRunDTO.from_entity(created)
