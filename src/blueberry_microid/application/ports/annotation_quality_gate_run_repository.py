from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun


class AnnotationQualityGateRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, quality_gate_run: AnnotationQualityGateRun) -> AnnotationQualityGateRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, quality_gate_run_id: UUID) -> Optional[AnnotationQualityGateRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[AnnotationQualityGateRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[AnnotationQualityGateRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_annotation_bundle_run_id(self, annotation_bundle_run_id: UUID) -> list[AnnotationQualityGateRun]:
        raise NotImplementedError
