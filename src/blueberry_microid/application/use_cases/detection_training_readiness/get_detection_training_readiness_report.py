from uuid import UUID

from blueberry_microid.application.dto.detection_training_readiness_dto import DetectionTrainingReadinessReportDTO
from blueberry_microid.application.exceptions import DetectionTrainingReadinessReportNotFoundError
from blueberry_microid.application.ports.detection_training_readiness_report_repository import (
    DetectionTrainingReadinessReportRepositoryPort,
)


class GetDetectionTrainingReadinessReportUseCase:
    def __init__(self, report_repository: DetectionTrainingReadinessReportRepositoryPort) -> None:
        self._report_repository = report_repository

    def execute(self, readiness_report_id: UUID) -> DetectionTrainingReadinessReportDTO:
        report = self._report_repository.get_by_id(readiness_report_id)
        if report is None:
            raise DetectionTrainingReadinessReportNotFoundError(
                f"detection_training_readiness_report '{readiness_report_id}' does not exist"
            )
        return DetectionTrainingReadinessReportDTO.from_entity(report)
