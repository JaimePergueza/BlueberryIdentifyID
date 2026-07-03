from uuid import UUID

from blueberry_microid.application.dto.annotation_quality_gate_dto import AnnotationQualityGateRunDTO
from blueberry_microid.application.exceptions import AnnotationQualityGateRunNotFoundError
from blueberry_microid.application.ports.annotation_quality_gate_run_repository import (
    AnnotationQualityGateRunRepositoryPort,
)


class GetAnnotationQualityGateRunUseCase:
    def __init__(self, run_repository: AnnotationQualityGateRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(self, quality_gate_run_id: UUID) -> AnnotationQualityGateRunDTO:
        run = self._run_repository.get_by_id(quality_gate_run_id)
        if run is None:
            raise AnnotationQualityGateRunNotFoundError(f"annotation_quality_gate_run '{quality_gate_run_id}' does not exist")
        return AnnotationQualityGateRunDTO.from_entity(run)
