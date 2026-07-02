from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.model_version_dto import CreateModelVersionRequest
from blueberry_microid.application.use_cases.model_version.create_model_version import CreateModelVersionUseCase
from blueberry_microid.application.use_cases.model_version.list_model_versions import ListModelVersionsUseCase
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_model_version_use_case,
    get_list_model_versions_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.model_version import ModelVersionCreate, ModelVersionRead

router = APIRouter(prefix="/model-versions", tags=["model-versions"])


@router.post("", response_model=ModelVersionRead, status_code=status.HTTP_201_CREATED)
def create_model_version(
    payload: ModelVersionCreate,
    use_case: CreateModelVersionUseCase = Depends(get_create_model_version_use_case),
) -> ModelVersionRead:
    # payload.model_type is already a validated ModelType enum member (mock
    # /pytorch/external) — Pydantic rejects anything else with a 422 before
    # this handler ever runs. .value converts it to the plain str the
    # application-layer DTO expects (application/ never imports Pydantic).
    request = CreateModelVersionRequest(
        name=payload.name,
        version=payload.version,
        model_type=payload.model_type.value,
        description=payload.description,
        is_active=payload.is_active,
    )
    dto = use_case.execute(request)
    return ModelVersionRead.model_validate(dto)


@router.get("", response_model=list[ModelVersionRead])
def list_model_versions(
    use_case: ListModelVersionsUseCase = Depends(get_list_model_versions_use_case),
) -> list[ModelVersionRead]:
    dtos = use_case.execute()
    return [ModelVersionRead.model_validate(dto) for dto in dtos]
