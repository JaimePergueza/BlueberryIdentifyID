from blueberry_microid.application.dto.model_version_dto import ModelVersionDTO
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort


class ListModelVersionsUseCase:
    """Lists every registered inference-engine version, oldest first."""

    def __init__(self, model_version_repository: ModelVersionRepositoryPort) -> None:
        self._model_version_repository = model_version_repository

    def execute(self) -> list[ModelVersionDTO]:
        model_versions = self._model_version_repository.list_all()
        return [ModelVersionDTO.from_entity(model_version) for model_version in model_versions]
