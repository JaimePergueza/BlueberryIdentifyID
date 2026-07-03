from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_readiness_report import (
    DetectionTrainingReadinessReport,
)


class DetectionTrainingReadinessReportRepositoryPort(ABC):
    @abstractmethod
    def add(self, report: DetectionTrainingReadinessReport) -> DetectionTrainingReadinessReport:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, report_id: UUID) -> Optional[DetectionTrainingReadinessReport]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DetectionTrainingReadinessReport]:
        raise NotImplementedError

    @abstractmethod
    def list_by_detection_training_run_id(
        self, detection_training_run_id: UUID
    ) -> list[DetectionTrainingReadinessReport]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingReadinessReport]:
        raise NotImplementedError

    @abstractmethod
    def list_by_annotation_bundle_run_id(
        self, annotation_bundle_run_id: UUID
    ) -> list[DetectionTrainingReadinessReport]:
        raise NotImplementedError

    @abstractmethod
    def list_by_annotation_quality_gate_run_id(
        self, annotation_quality_gate_run_id: UUID
    ) -> list[DetectionTrainingReadinessReport]:
        raise NotImplementedError
