from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.detection_training_readiness_dto import DetectionTrainingReadinessReportDTO
from blueberry_microid.application.ports.detection_training_readiness_report_repository import (
    DetectionTrainingReadinessReportRepositoryPort,
)


class ListDetectionTrainingReadinessReportsUseCase:
    def __init__(self, report_repository: DetectionTrainingReadinessReportRepositoryPort) -> None:
        self._report_repository = report_repository

    def execute(
        self,
        *,
        detection_training_run_id: Optional[UUID] = None,
        dataset_release_id: Optional[UUID] = None,
        annotation_bundle_run_id: Optional[UUID] = None,
        annotation_quality_gate_run_id: Optional[UUID] = None,
    ) -> list[DetectionTrainingReadinessReportDTO]:
        if detection_training_run_id is not None:
            reports = self._report_repository.list_by_detection_training_run_id(detection_training_run_id)
        elif dataset_release_id is not None:
            reports = self._report_repository.list_by_dataset_release_id(dataset_release_id)
        elif annotation_bundle_run_id is not None:
            reports = self._report_repository.list_by_annotation_bundle_run_id(annotation_bundle_run_id)
        elif annotation_quality_gate_run_id is not None:
            reports = self._report_repository.list_by_annotation_quality_gate_run_id(
                annotation_quality_gate_run_id
            )
        else:
            reports = self._report_repository.list_all()
        return [DetectionTrainingReadinessReportDTO.from_entity(report) for report in reports]
