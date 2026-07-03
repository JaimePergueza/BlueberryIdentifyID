from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile


class AnnotationBundleFileRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, files: list[AnnotationBundleFile]) -> list[AnnotationBundleFile]:
        raise NotImplementedError

    @abstractmethod
    def list_by_bundle_run_id(self, bundle_run_id: UUID) -> list[AnnotationBundleFile]:
        raise NotImplementedError
