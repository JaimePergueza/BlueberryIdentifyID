from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.detection_training_environment_dto import (
    DetectionTrainingEnvironmentSpecDTO,
)
from blueberry_microid.application.ports.detection_training_environment_spec_repository import (
    DetectionTrainingEnvironmentSpecRepositoryPort,
)


class ListDetectionTrainingEnvironmentSpecsUseCase:
    def __init__(self, spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort) -> None:
        self._spec_repository = spec_repository

    def execute(
        self,
        *,
        detection_training_run_id: Optional[UUID] = None,
        readiness_report_id: Optional[UUID] = None,
        annotation_bundle_run_id: Optional[UUID] = None,
        dataset_release_id: Optional[UUID] = None,
    ) -> list[DetectionTrainingEnvironmentSpecDTO]:
        if detection_training_run_id is not None:
            specs = self._spec_repository.list_by_detection_training_run_id(detection_training_run_id)
        elif readiness_report_id is not None:
            specs = self._spec_repository.list_by_readiness_report_id(readiness_report_id)
        elif annotation_bundle_run_id is not None:
            specs = self._spec_repository.list_by_annotation_bundle_run_id(annotation_bundle_run_id)
        elif dataset_release_id is not None:
            specs = self._spec_repository.list_by_dataset_release_id(dataset_release_id)
        else:
            specs = self._spec_repository.list_all()
        return [DetectionTrainingEnvironmentSpecDTO.from_entity(spec) for spec in specs]
