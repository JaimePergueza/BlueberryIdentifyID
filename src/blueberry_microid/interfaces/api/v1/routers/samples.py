from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.sample_dto import CreateSampleRequest
from blueberry_microid.application.use_cases.sample.create_sample import CreateSampleUseCase
from blueberry_microid.application.use_cases.sample.get_sample import (
    GetSampleByIdUseCase,
    GetSampleBySampleCodeUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_sample_use_case,
    get_get_sample_by_code_use_case,
    get_get_sample_by_id_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.sample import SampleCreate, SampleRead

router = APIRouter(prefix="/samples", tags=["samples"])


@router.post("", response_model=SampleRead, status_code=status.HTTP_201_CREATED)
def create_sample(
    payload: SampleCreate,
    use_case: CreateSampleUseCase = Depends(get_create_sample_use_case),
) -> SampleRead:
    request = CreateSampleRequest(
        sample_code=payload.sample_code,
        lot_code=payload.lot_code,
        origin=payload.origin,
        collection_date=payload.collection_date,
        notes=payload.notes,
    )
    dto = use_case.execute(request)
    return SampleRead.model_validate(dto)


# Registered before "/{sample_id}" — otherwise FastAPI would try to parse
# the literal segment "by-code" as a UUID path parameter and fail with a
# spurious 422 instead of reaching this route.
@router.get("/by-code/{sample_code}", response_model=SampleRead)
def get_sample_by_code(
    sample_code: str,
    use_case: GetSampleBySampleCodeUseCase = Depends(get_get_sample_by_code_use_case),
) -> SampleRead:
    dto = use_case.execute(sample_code)
    return SampleRead.model_validate(dto)


@router.get("/{sample_id}", response_model=SampleRead)
def get_sample_by_id(
    sample_id: UUID,
    use_case: GetSampleByIdUseCase = Depends(get_get_sample_by_id_use_case),
) -> SampleRead:
    dto = use_case.execute(sample_id)
    return SampleRead.model_validate(dto)
