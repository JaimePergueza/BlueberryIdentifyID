from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_artifact_record import DetectionTrainingArtifactRecord


class DetectionTrainingArtifactRecordRepositoryPort(ABC):
    @abstractmethod
    def add_many(
        self, records: list[DetectionTrainingArtifactRecord]
    ) -> list[DetectionTrainingArtifactRecord]:
        raise NotImplementedError

    @abstractmethod
    def list_by_artifact_policy_id(self, artifact_policy_id: UUID) -> list[DetectionTrainingArtifactRecord]:
        raise NotImplementedError
