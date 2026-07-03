from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.annotation_bundle_dto import (
    AnnotationBundleConfigDTO,
    CreateAnnotationBundleRunRequest,
)
from blueberry_microid.application.use_cases.annotation_bundle.create_annotation_bundle_run import (
    CreateAnnotationBundleRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_bundle.get_annotation_bundle_run import (
    GetAnnotationBundleRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_bundle.list_annotation_bundle_files import (
    ListAnnotationBundleFilesUseCase,
)
from blueberry_microid.application.use_cases.annotation_bundle.list_annotation_bundle_runs import (
    ListAnnotationBundleRunsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_annotation_bundle_run_use_case,
    get_get_annotation_bundle_run_use_case,
    get_list_annotation_bundle_files_use_case,
    get_list_annotation_bundle_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.annotation_bundle import (
    AnnotationBundleCreate,
    AnnotationBundleFileListResponse,
    AnnotationBundleFileResponse,
    AnnotationBundleListResponse,
    AnnotationBundleRunResponse,
)

router = APIRouter(tags=["annotation-bundles"])


@router.post("/ml/annotation-bundles", response_model=AnnotationBundleRunResponse, status_code=status.HTTP_201_CREATED)
def create_annotation_bundle(
    payload: AnnotationBundleCreate,
    use_case: CreateAnnotationBundleRunUseCase = Depends(get_create_annotation_bundle_run_use_case),
) -> AnnotationBundleRunResponse:
    dto = use_case.execute(
        CreateAnnotationBundleRunRequest(
            petri_annotation_export_run_id=payload.petri_annotation_export_run_id,
            config=AnnotationBundleConfigDTO(**payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return AnnotationBundleRunResponse.model_validate(dto)


@router.get("/ml/annotation-bundles", response_model=AnnotationBundleListResponse)
def list_annotation_bundles(
    use_case: ListAnnotationBundleRunsUseCase = Depends(get_list_annotation_bundle_runs_use_case),
) -> AnnotationBundleListResponse:
    return AnnotationBundleListResponse(
        bundles=[AnnotationBundleRunResponse.model_validate(dto) for dto in use_case.execute()]
    )


@router.get("/ml/annotation-bundles/{bundle_run_id}", response_model=AnnotationBundleRunResponse)
def get_annotation_bundle(
    bundle_run_id: UUID,
    use_case: GetAnnotationBundleRunUseCase = Depends(get_get_annotation_bundle_run_use_case),
) -> AnnotationBundleRunResponse:
    return AnnotationBundleRunResponse.model_validate(use_case.execute(bundle_run_id))


@router.get("/ml/annotation-bundles/{bundle_run_id}/files", response_model=AnnotationBundleFileListResponse)
def list_annotation_bundle_files(
    bundle_run_id: UUID,
    use_case: ListAnnotationBundleFilesUseCase = Depends(get_list_annotation_bundle_files_use_case),
) -> AnnotationBundleFileListResponse:
    return AnnotationBundleFileListResponse(
        files=[AnnotationBundleFileResponse.model_validate(dto) for dto in use_case.execute(bundle_run_id)]
    )


@router.get("/datasets/releases/{dataset_release_id}/annotation-bundles", response_model=AnnotationBundleListResponse)
def list_annotation_bundles_for_release(
    dataset_release_id: UUID,
    use_case: ListAnnotationBundleRunsUseCase = Depends(get_list_annotation_bundle_runs_use_case),
) -> AnnotationBundleListResponse:
    return AnnotationBundleListResponse(
        bundles=[
            AnnotationBundleRunResponse.model_validate(dto)
            for dto in use_case.execute(dataset_release_id=dataset_release_id)
        ]
    )


@router.get(
    "/ml/petri-annotation-exports/{export_run_id}/annotation-bundles",
    response_model=AnnotationBundleListResponse,
)
def list_annotation_bundles_for_export(
    export_run_id: UUID,
    use_case: ListAnnotationBundleRunsUseCase = Depends(get_list_annotation_bundle_runs_use_case),
) -> AnnotationBundleListResponse:
    return AnnotationBundleListResponse(
        bundles=[
            AnnotationBundleRunResponse.model_validate(dto)
            for dto in use_case.execute(petri_annotation_export_run_id=export_run_id)
        ]
    )
