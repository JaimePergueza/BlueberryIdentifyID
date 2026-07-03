from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.petri_annotation_export_dto import (
    CreatePetriAnnotationExportRunRequest,
    PetriAnnotationExportConfigDTO,
)
from blueberry_microid.application.use_cases.petri_annotation_export.create_petri_annotation_export_run import (
    CreatePetriAnnotationExportRunUseCase,
)
from blueberry_microid.application.use_cases.petri_annotation_export.get_petri_annotation_export_run import (
    GetPetriAnnotationExportRunUseCase,
)
from blueberry_microid.application.use_cases.petri_annotation_export.list_petri_annotation_export_items import (
    ListPetriAnnotationExportItemsUseCase,
)
from blueberry_microid.application.use_cases.petri_annotation_export.list_petri_annotation_export_runs import (
    ListPetriAnnotationExportRunsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_petri_annotation_export_run_use_case,
    get_get_petri_annotation_export_run_use_case,
    get_list_petri_annotation_export_items_use_case,
    get_list_petri_annotation_export_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.petri_annotation_export import (
    PetriAnnotationExportCreate,
    PetriAnnotationExportItemListResponse,
    PetriAnnotationExportItemResponse,
    PetriAnnotationExportListResponse,
    PetriAnnotationExportRunResponse,
)

router = APIRouter(tags=["petri-annotation-exports"])


@router.post(
    "/ml/petri-annotation-exports",
    response_model=PetriAnnotationExportRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_petri_annotation_export(
    payload: PetriAnnotationExportCreate,
    use_case: CreatePetriAnnotationExportRunUseCase = Depends(get_create_petri_annotation_export_run_use_case),
) -> PetriAnnotationExportRunResponse:
    dto = use_case.execute(
        CreatePetriAnnotationExportRunRequest(
            dataset_release_id=payload.dataset_release_id,
            petri_segmentation_run_id=payload.petri_segmentation_run_id,
            config=PetriAnnotationExportConfigDTO(**payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return PetriAnnotationExportRunResponse.model_validate(dto)


@router.get("/ml/petri-annotation-exports", response_model=PetriAnnotationExportListResponse)
def list_petri_annotation_exports(
    use_case: ListPetriAnnotationExportRunsUseCase = Depends(get_list_petri_annotation_export_runs_use_case),
) -> PetriAnnotationExportListResponse:
    return PetriAnnotationExportListResponse(
        exports=[PetriAnnotationExportRunResponse.model_validate(dto) for dto in use_case.execute()]
    )


@router.get("/ml/petri-annotation-exports/{export_run_id}", response_model=PetriAnnotationExportRunResponse)
def get_petri_annotation_export(
    export_run_id: UUID,
    use_case: GetPetriAnnotationExportRunUseCase = Depends(get_get_petri_annotation_export_run_use_case),
) -> PetriAnnotationExportRunResponse:
    return PetriAnnotationExportRunResponse.model_validate(use_case.execute(export_run_id))


@router.get(
    "/ml/petri-annotation-exports/{export_run_id}/items",
    response_model=PetriAnnotationExportItemListResponse,
)
def list_petri_annotation_export_items(
    export_run_id: UUID,
    use_case: ListPetriAnnotationExportItemsUseCase = Depends(get_list_petri_annotation_export_items_use_case),
) -> PetriAnnotationExportItemListResponse:
    return PetriAnnotationExportItemListResponse(
        items=[PetriAnnotationExportItemResponse.model_validate(dto) for dto in use_case.execute(export_run_id)]
    )


@router.get("/ml/petri-annotation-exports/{export_run_id}/manifest", response_model=dict)
def get_petri_annotation_export_manifest(
    export_run_id: UUID,
    use_case: GetPetriAnnotationExportRunUseCase = Depends(get_get_petri_annotation_export_run_use_case),
) -> dict:
    return use_case.execute(export_run_id).output_manifest


@router.get(
    "/datasets/releases/{dataset_release_id}/petri-annotation-exports",
    response_model=PetriAnnotationExportListResponse,
)
def list_petri_annotation_exports_for_dataset_release(
    dataset_release_id: UUID,
    use_case: ListPetriAnnotationExportRunsUseCase = Depends(get_list_petri_annotation_export_runs_use_case),
) -> PetriAnnotationExportListResponse:
    return PetriAnnotationExportListResponse(
        exports=[
            PetriAnnotationExportRunResponse.model_validate(dto)
            for dto in use_case.execute(dataset_release_id=dataset_release_id)
        ]
    )


@router.get(
    "/ml/petri-segmentations/{petri_segmentation_run_id}/annotation-exports",
    response_model=PetriAnnotationExportListResponse,
)
def list_petri_annotation_exports_for_segmentation_run(
    petri_segmentation_run_id: UUID,
    use_case: ListPetriAnnotationExportRunsUseCase = Depends(get_list_petri_annotation_export_runs_use_case),
) -> PetriAnnotationExportListResponse:
    return PetriAnnotationExportListResponse(
        exports=[
            PetriAnnotationExportRunResponse.model_validate(dto)
            for dto in use_case.execute(petri_segmentation_run_id=petri_segmentation_run_id)
        ]
    )
