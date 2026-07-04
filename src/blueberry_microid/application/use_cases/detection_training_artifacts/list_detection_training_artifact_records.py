from uuid import UUID

from blueberry_microid.application.dto.detection_training_artifact_dto import DetectionTrainingArtifactRecordDTO
from blueberry_microid.application.exceptions import DetectionTrainingArtifactPolicyNotFoundError
from blueberry_microid.application.ports.detection_training_artifact_policy_repository import (
    DetectionTrainingArtifactPolicyRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_artifact_record_repository import (
    DetectionTrainingArtifactRecordRepositoryPort,
)


class ListDetectionTrainingArtifactRecordsUseCase:
    def __init__(
        self,
        policy_repository: DetectionTrainingArtifactPolicyRepositoryPort,
        record_repository: DetectionTrainingArtifactRecordRepositoryPort,
    ) -> None:
        self._policy_repository = policy_repository
        self._record_repository = record_repository

    def execute(self, artifact_policy_id: UUID) -> list[DetectionTrainingArtifactRecordDTO]:
        if self._policy_repository.get_by_id(artifact_policy_id) is None:
            raise DetectionTrainingArtifactPolicyNotFoundError(
                f"detection_training_artifact_policy '{artifact_policy_id}' does not exist"
            )
        return [
            DetectionTrainingArtifactRecordDTO.from_entity(record)
            for record in self._record_repository.list_by_artifact_policy_id(artifact_policy_id)
        ]
