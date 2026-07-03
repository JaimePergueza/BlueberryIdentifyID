from uuid import UUID

from blueberry_microid.application.dto.annotation_bundle_dto import AnnotationBundleRunDTO
from blueberry_microid.application.exceptions import AnnotationBundleRunNotFoundError
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort


class GetAnnotationBundleRunUseCase:
    def __init__(self, run_repository: AnnotationBundleRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(self, bundle_run_id: UUID) -> AnnotationBundleRunDTO:
        run = self._run_repository.get_by_id(bundle_run_id)
        if run is None:
            raise AnnotationBundleRunNotFoundError(f"annotation_bundle_run '{bundle_run_id}' does not exist")
        return AnnotationBundleRunDTO.from_entity(run)
