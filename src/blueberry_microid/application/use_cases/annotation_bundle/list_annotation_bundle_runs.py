from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.annotation_bundle_dto import AnnotationBundleRunDTO
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort


class ListAnnotationBundleRunsUseCase:
    def __init__(self, run_repository: AnnotationBundleRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(
        self,
        *,
        dataset_release_id: Optional[UUID] = None,
        petri_annotation_export_run_id: Optional[UUID] = None,
    ) -> list[AnnotationBundleRunDTO]:
        if dataset_release_id is not None:
            runs = self._run_repository.list_by_dataset_release_id(dataset_release_id)
        elif petri_annotation_export_run_id is not None:
            runs = self._run_repository.list_by_petri_annotation_export_run_id(petri_annotation_export_run_id)
        else:
            runs = self._run_repository.list_all()
        return [AnnotationBundleRunDTO.from_entity(run) for run in runs]
