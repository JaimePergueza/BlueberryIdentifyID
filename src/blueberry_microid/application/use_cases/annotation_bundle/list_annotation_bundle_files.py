from uuid import UUID

from blueberry_microid.application.dto.annotation_bundle_dto import AnnotationBundleFileDTO
from blueberry_microid.application.exceptions import AnnotationBundleRunNotFoundError
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort


class ListAnnotationBundleFilesUseCase:
    def __init__(
        self,
        run_repository: AnnotationBundleRunRepositoryPort,
        file_repository: AnnotationBundleFileRepositoryPort,
    ) -> None:
        self._run_repository = run_repository
        self._file_repository = file_repository

    def execute(self, bundle_run_id: UUID) -> list[AnnotationBundleFileDTO]:
        if self._run_repository.get_by_id(bundle_run_id) is None:
            raise AnnotationBundleRunNotFoundError(f"annotation_bundle_run '{bundle_run_id}' does not exist")
        return [AnnotationBundleFileDTO.from_entity(file) for file in self._file_repository.list_by_bundle_run_id(bundle_run_id)]
