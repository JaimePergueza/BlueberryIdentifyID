from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from blueberry_microid.application.dto.image_feature_extraction_dto import CreateImageFeatureExtractionRunRequest
from blueberry_microid.application.use_cases.image_feature_extraction.create_image_feature_extraction_run import (
    CreateImageFeatureExtractionRunUseCase,
)
from blueberry_microid.application.use_cases.image_feature_extraction.get_image_feature_extraction_run import (
    GetImageFeatureExtractionRunUseCase,
)
from blueberry_microid.application.use_cases.image_feature_extraction.list_image_feature_extraction_runs import (
    ListImageFeatureExtractionRunsUseCase,
)
from blueberry_microid.application.use_cases.image_feature_extraction.list_image_feature_vectors import (
    ListImageFeatureVectorsUseCase,
)
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_image_feature_extraction_run_use_case,
    get_get_image_feature_extraction_run_use_case,
    get_list_image_feature_extraction_runs_use_case,
    get_list_image_feature_vectors_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.image_feature_extraction import (
    CreateImageFeatureExtractionRunRequestBody,
    ImageFeatureExtractionRunResponse,
    ImageFeatureVectorResponse,
)
from blueberry_microid.ml.configs.image_feature_extraction_config import ImageFeatureExtractionConfig

router = APIRouter(tags=["image-feature-extractions"])


@router.post(
    "/ml/image-feature-extractions",
    response_model=ImageFeatureExtractionRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_image_feature_extraction_run(
    payload: CreateImageFeatureExtractionRunRequestBody,
    use_case: CreateImageFeatureExtractionRunUseCase = Depends(get_create_image_feature_extraction_run_use_case),
) -> ImageFeatureExtractionRunResponse:
    dto = use_case.execute(
        CreateImageFeatureExtractionRunRequest(
            dataset_release_id=payload.dataset_release_id,
            image_audit_run_id=payload.image_audit_run_id,
            config=ImageFeatureExtractionConfig.from_dict(payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return ImageFeatureExtractionRunResponse.model_validate(dto)


@router.get("/ml/image-feature-extractions", response_model=list[ImageFeatureExtractionRunResponse])
def list_image_feature_extraction_runs(
    use_case: ListImageFeatureExtractionRunsUseCase = Depends(get_list_image_feature_extraction_runs_use_case),
) -> list[ImageFeatureExtractionRunResponse]:
    return [ImageFeatureExtractionRunResponse.model_validate(dto) for dto in use_case.execute()]


@router.get(
    "/ml/image-feature-extractions/{feature_extraction_run_id}", response_model=ImageFeatureExtractionRunResponse
)
def get_image_feature_extraction_run(
    feature_extraction_run_id: UUID,
    use_case: GetImageFeatureExtractionRunUseCase = Depends(get_get_image_feature_extraction_run_use_case),
) -> ImageFeatureExtractionRunResponse:
    return ImageFeatureExtractionRunResponse.model_validate(use_case.execute(feature_extraction_run_id))


@router.get(
    "/ml/image-feature-extractions/{feature_extraction_run_id}/vectors",
    response_model=list[ImageFeatureVectorResponse],
)
def list_image_feature_vectors(
    feature_extraction_run_id: UUID,
    modality: Optional[ImageModality] = Query(default=None),
    split: Optional[DatasetSplit] = Query(default=None),
    use_case: ListImageFeatureVectorsUseCase = Depends(get_list_image_feature_vectors_use_case),
) -> list[ImageFeatureVectorResponse]:
    return [
        ImageFeatureVectorResponse.model_validate(dto)
        for dto in use_case.execute(feature_extraction_run_id, modality=modality, split=split)
    ]


@router.get(
    "/datasets/releases/{dataset_release_id}/image-feature-extractions",
    response_model=list[ImageFeatureExtractionRunResponse],
)
def list_image_feature_extraction_runs_for_release(
    dataset_release_id: UUID,
    use_case: ListImageFeatureExtractionRunsUseCase = Depends(get_list_image_feature_extraction_runs_use_case),
) -> list[ImageFeatureExtractionRunResponse]:
    return [
        ImageFeatureExtractionRunResponse.model_validate(dto)
        for dto in use_case.execute(dataset_release_id=dataset_release_id)
    ]


@router.get(
    "/ml/image-audits/{image_audit_run_id}/feature-extractions",
    response_model=list[ImageFeatureExtractionRunResponse],
)
def list_image_feature_extraction_runs_for_audit(
    image_audit_run_id: UUID,
    use_case: ListImageFeatureExtractionRunsUseCase = Depends(get_list_image_feature_extraction_runs_use_case),
) -> list[ImageFeatureExtractionRunResponse]:
    return [
        ImageFeatureExtractionRunResponse.model_validate(dto)
        for dto in use_case.execute(image_audit_run_id=image_audit_run_id)
    ]
