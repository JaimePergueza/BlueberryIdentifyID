from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_artifact_policy import DetectionTrainingArtifactPolicy


class DetectionTrainingArtifactPolicyRepositoryPort(ABC):
    @abstractmethod
    def add(self, policy: DetectionTrainingArtifactPolicy) -> DetectionTrainingArtifactPolicy:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, policy_id: UUID) -> Optional[DetectionTrainingArtifactPolicy]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DetectionTrainingArtifactPolicy]:
        raise NotImplementedError

    @abstractmethod
    def list_by_detection_training_run_id(
        self, detection_training_run_id: UUID
    ) -> list[DetectionTrainingArtifactPolicy]:
        raise NotImplementedError

    @abstractmethod
    def list_by_readiness_report_id(self, readiness_report_id: UUID) -> list[DetectionTrainingArtifactPolicy]:
        raise NotImplementedError

    @abstractmethod
    def list_by_environment_spec_id(self, environment_spec_id: UUID) -> list[DetectionTrainingArtifactPolicy]:
        raise NotImplementedError

    @abstractmethod
    def list_by_annotation_bundle_run_id(
        self, annotation_bundle_run_id: UUID
    ) -> list[DetectionTrainingArtifactPolicy]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingArtifactPolicy]:
        raise NotImplementedError
