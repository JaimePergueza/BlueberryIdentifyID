from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.annotation_quality_gate_dto import AnnotationQualityGateRunDTO
from blueberry_microid.application.ports.annotation_quality_gate_run_repository import (
    AnnotationQualityGateRunRepositoryPort,
)


class ListAnnotationQualityGateRunsUseCase:
    def __init__(self, run_repository: AnnotationQualityGateRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(
        self,
        *,
        dataset_release_id: Optional[UUID] = None,
        annotation_bundle_run_id: Optional[UUID] = None,
    ) -> list[AnnotationQualityGateRunDTO]:
        if dataset_release_id is not None:
            runs = self._run_repository.list_by_dataset_release_id(dataset_release_id)
        elif annotation_bundle_run_id is not None:
            runs = self._run_repository.list_by_annotation_bundle_run_id(annotation_bundle_run_id)
        else:
            runs = self._run_repository.list_all()
        return [AnnotationQualityGateRunDTO.from_entity(run) for run in runs]
