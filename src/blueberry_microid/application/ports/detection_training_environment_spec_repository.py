from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec


class DetectionTrainingEnvironmentSpecRepositoryPort(ABC):
    @abstractmethod
    def add(self, spec: DetectionTrainingEnvironmentSpec) -> DetectionTrainingEnvironmentSpec:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, spec_id: UUID) -> Optional[DetectionTrainingEnvironmentSpec]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DetectionTrainingEnvironmentSpec]:
        raise NotImplementedError

    @abstractmethod
    def list_by_detection_training_run_id(
        self, detection_training_run_id: UUID
    ) -> list[DetectionTrainingEnvironmentSpec]:
        raise NotImplementedError

    @abstractmethod
    def list_by_readiness_report_id(self, readiness_report_id: UUID) -> list[DetectionTrainingEnvironmentSpec]:
        raise NotImplementedError

    @abstractmethod
    def list_by_annotation_bundle_run_id(
        self, annotation_bundle_run_id: UUID
    ) -> list[DetectionTrainingEnvironmentSpec]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingEnvironmentSpec]:
        raise NotImplementedError
