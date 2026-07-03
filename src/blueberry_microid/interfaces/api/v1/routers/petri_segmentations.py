from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from blueberry_microid.application.dto.petri_segmentation_dto import CreatePetriSegmentationRunRequest
from blueberry_microid.application.use_cases.petri_segmentation.create_petri_segmentation_run import (
    CreatePetriSegmentationRunUseCase,
)
from blueberry_microid.application.use_cases.petri_segmentation.get_petri_segmentation_run import (
    GetPetriSegmentationRunUseCase,
)
from blueberry_microid.application.use_cases.petri_segmentation.list_petri_segmentation_regions import (
    ListPetriSegmentationRegionsUseCase,
)
from blueberry_microid.application.use_cases.petri_segmentation.list_petri_segmentation_runs import (
    ListPetriSegmentationRunsUseCase,
)
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_petri_segmentation_run_use_case,
    get_get_petri_segmentation_run_use_case,
    get_list_petri_segmentation_regions_use_case,
    get_list_petri_segmentation_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.petri_segmentation import (
    CreatePetriSegmentationRunRequestBody,
    PetriSegmentationRegionResponse,
    PetriSegmentationRunResponse,
)
from blueberry_microid.ml.configs.petri_segmentation_config import PetriSegmentationConfig

router = APIRouter(tags=["petri-segmentations"])


@router.post(
    "/ml/petri-segmentations",
    response_model=PetriSegmentationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_petri_segmentation_run(
    payload: CreatePetriSegmentationRunRequestBody,
    use_case: CreatePetriSegmentationRunUseCase = Depends(get_create_petri_segmentation_run_use_case),
) -> PetriSegmentationRunResponse:
    dto = use_case.execute(
        CreatePetriSegmentationRunRequest(
            dataset_release_id=payload.dataset_release_id,
            image_audit_run_id=payload.image_audit_run_id,
            config=PetriSegmentationConfig.from_dict(payload.petri_segmentation_config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return PetriSegmentationRunResponse.model_validate(dto)


@router.get("/ml/petri-segmentations", response_model=list[PetriSegmentationRunResponse])
def list_petri_segmentation_runs(
    dataset_release_id: UUID | None = Query(default=None),
    image_audit_run_id: UUID | None = Query(default=None),
    use_case: ListPetriSegmentationRunsUseCase = Depends(get_list_petri_segmentation_runs_use_case),
) -> list[PetriSegmentationRunResponse]:
    return [
        PetriSegmentationRunResponse.model_validate(dto)
        for dto in use_case.execute(dataset_release_id=dataset_release_id, image_audit_run_id=image_audit_run_id)
    ]


@router.get("/ml/petri-segmentations/{segmentation_run_id}", response_model=PetriSegmentationRunResponse)
def get_petri_segmentation_run(
    segmentation_run_id: UUID,
    use_case: GetPetriSegmentationRunUseCase = Depends(get_get_petri_segmentation_run_use_case),
) -> PetriSegmentationRunResponse:
    return PetriSegmentationRunResponse.model_validate(use_case.execute(segmentation_run_id))


@router.get(
    "/ml/petri-segmentations/{segmentation_run_id}/regions",
    response_model=list[PetriSegmentationRegionResponse],
)
def list_petri_segmentation_regions(
    segmentation_run_id: UUID,
    split: DatasetSplit | None = Query(default=None),
    use_case: ListPetriSegmentationRegionsUseCase = Depends(get_list_petri_segmentation_regions_use_case),
) -> list[PetriSegmentationRegionResponse]:
    return [
        PetriSegmentationRegionResponse.model_validate(dto)
        for dto in use_case.execute(segmentation_run_id, split=split)
    ]


@router.get(
    "/datasets/releases/{dataset_release_id}/petri-segmentations",
    response_model=list[PetriSegmentationRunResponse],
)
def list_petri_segmentation_runs_for_release(
    dataset_release_id: UUID,
    use_case: ListPetriSegmentationRunsUseCase = Depends(get_list_petri_segmentation_runs_use_case),
) -> list[PetriSegmentationRunResponse]:
    return [
        PetriSegmentationRunResponse.model_validate(dto)
        for dto in use_case.execute(dataset_release_id=dataset_release_id)
    ]


@router.get(
    "/ml/image-audits/{image_audit_run_id}/petri-segmentations",
    response_model=list[PetriSegmentationRunResponse],
)
def list_petri_segmentation_runs_for_audit(
    image_audit_run_id: UUID,
    use_case: ListPetriSegmentationRunsUseCase = Depends(get_list_petri_segmentation_runs_use_case),
) -> list[PetriSegmentationRunResponse]:
    return [
        PetriSegmentationRunResponse.model_validate(dto)
        for dto in use_case.execute(image_audit_run_id=image_audit_run_id)
    ]
