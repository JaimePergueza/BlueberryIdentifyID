from uuid import UUID

from blueberry_microid.application.dto.detection_training_environment_dto import (
    DetectionTrainingEnvironmentSpecDTO,
)
from blueberry_microid.application.exceptions import DetectionTrainingEnvironmentSpecNotFoundError
from blueberry_microid.application.ports.detection_training_environment_spec_repository import (
    DetectionTrainingEnvironmentSpecRepositoryPort,
)


class GetDetectionTrainingEnvironmentSpecUseCase:
    def __init__(self, spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort) -> None:
        self._spec_repository = spec_repository

    def execute(self, environment_spec_id: UUID) -> DetectionTrainingEnvironmentSpecDTO:
        spec = self._spec_repository.get_by_id(environment_spec_id)
        if spec is None:
            raise DetectionTrainingEnvironmentSpecNotFoundError(
                f"detection_training_environment_spec '{environment_spec_id}' does not exist"
            )
        return DetectionTrainingEnvironmentSpecDTO.from_entity(spec)
