from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun


class DetectionTrainingRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, run: DetectionTrainingRun) -> DetectionTrainingRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, run_id: UUID) -> Optional[DetectionTrainingRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DetectionTrainingRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_annotation_bundle_run_id(self, annotation_bundle_run_id: UUID) -> list[DetectionTrainingRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_annotation_quality_gate_run_id(
        self, annotation_quality_gate_run_id: UUID
    ) -> list[DetectionTrainingRun]:
        raise NotImplementedError
