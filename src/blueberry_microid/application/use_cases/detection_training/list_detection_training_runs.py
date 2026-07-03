from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.detection_training_dto import DetectionTrainingRunDTO
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort


class ListDetectionTrainingRunsUseCase:
    def __init__(self, run_repository: DetectionTrainingRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(
        self,
        *,
        dataset_release_id: Optional[UUID] = None,
        annotation_bundle_run_id: Optional[UUID] = None,
        annotation_quality_gate_run_id: Optional[UUID] = None,
    ) -> list[DetectionTrainingRunDTO]:
        if dataset_release_id is not None:
            runs = self._run_repository.list_by_dataset_release_id(dataset_release_id)
        elif annotation_bundle_run_id is not None:
            runs = self._run_repository.list_by_annotation_bundle_run_id(annotation_bundle_run_id)
        elif annotation_quality_gate_run_id is not None:
            runs = self._run_repository.list_by_annotation_quality_gate_run_id(annotation_quality_gate_run_id)
        else:
            runs = self._run_repository.list_all()
        return [DetectionTrainingRunDTO.from_entity(run) for run in runs]
