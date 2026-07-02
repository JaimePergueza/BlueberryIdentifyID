from blueberry_microid.application.dto.model_version_dto import CreateModelVersionRequest, ModelVersionDTO
from blueberry_microid.application.exceptions import InvalidModelTypeError
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.enums.model_type import ModelType


class CreateModelVersionUseCase:
    """Registers a traceable inference-engine version.

    Accepts `mock`, `pytorch`, and `external` model types. This use case
    never loads model weights or a real inference engine — it only records
    that a version exists, so future AnalysisRun/Prediction rows can
    reference it. Activating/deactivating a specific version is left for a
    future use case; `is_active` here only sets the initial flag.
    """

    def __init__(self, model_version_repository: ModelVersionRepositoryPort) -> None:
        self._model_version_repository = model_version_repository

    def execute(self, request: CreateModelVersionRequest) -> ModelVersionDTO:
        try:
            model_type = ModelType(request.model_type)
        except ValueError as exc:
            allowed = ", ".join(member.value for member in ModelType)
            raise InvalidModelTypeError(
                f"model_type '{request.model_type}' is not valid; expected one of: {allowed}"
            ) from exc

        model_version = ModelVersion(
            name=request.name,
            version=request.version,
            model_type=model_type,
            description=request.description,
            is_active=request.is_active,
        )
        created = self._model_version_repository.add(model_version)
        return ModelVersionDTO.from_entity(created)
