from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun


class AnnotationBundleRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, bundle_run: AnnotationBundleRun) -> AnnotationBundleRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, bundle_run_id: UUID) -> Optional[AnnotationBundleRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[AnnotationBundleRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[AnnotationBundleRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_petri_annotation_export_run_id(self, export_run_id: UUID) -> list[AnnotationBundleRun]:
        raise NotImplementedError
