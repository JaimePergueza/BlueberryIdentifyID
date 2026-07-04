from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_execution_run import DetectionTrainingExecutionRun


class DetectionTrainingExecutionRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, run: DetectionTrainingExecutionRun) -> DetectionTrainingExecutionRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, execution_run_id: UUID) -> Optional[DetectionTrainingExecutionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DetectionTrainingExecutionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_detection_training_run_id(
        self, detection_training_run_id: UUID
    ) -> list[DetectionTrainingExecutionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_readiness_report_id(self, readiness_report_id: UUID) -> list[DetectionTrainingExecutionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_environment_spec_id(self, environment_spec_id: UUID) -> list[DetectionTrainingExecutionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_artifact_policy_id(self, artifact_policy_id: UUID) -> list[DetectionTrainingExecutionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_annotation_bundle_run_id(
        self, annotation_bundle_run_id: UUID
    ) -> list[DetectionTrainingExecutionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingExecutionRun]:
        raise NotImplementedError
