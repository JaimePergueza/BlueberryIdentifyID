from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.image_audit_dto import CreateImageDatasetAuditRunRequest
from blueberry_microid.application.use_cases.image_audit.create_image_dataset_audit_run import (
    CreateImageDatasetAuditRunUseCase,
)
from blueberry_microid.application.use_cases.image_audit.get_image_dataset_audit_run import (
    GetImageDatasetAuditRunUseCase,
)
from blueberry_microid.application.use_cases.image_audit.list_image_dataset_audit_issues import (
    ListImageDatasetAuditIssuesUseCase,
)
from blueberry_microid.application.use_cases.image_audit.list_image_dataset_audit_runs import (
    ListImageDatasetAuditRunsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_image_dataset_audit_run_use_case,
    get_get_image_dataset_audit_run_use_case,
    get_list_image_dataset_audit_issues_use_case,
    get_list_image_dataset_audit_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.image_audit import (
    CreateImageDatasetAuditRunRequestBody,
    ImageDatasetAuditIssueResponse,
    ImageDatasetAuditRunResponse,
)
from blueberry_microid.ml.configs.image_audit_config import ImageAuditConfig

router = APIRouter(tags=["image-audits"])


@router.post("/ml/image-audits", response_model=ImageDatasetAuditRunResponse, status_code=status.HTTP_201_CREATED)
def create_image_dataset_audit_run(
    payload: CreateImageDatasetAuditRunRequestBody,
    use_case: CreateImageDatasetAuditRunUseCase = Depends(get_create_image_dataset_audit_run_use_case),
) -> ImageDatasetAuditRunResponse:
    dto = use_case.execute(
        CreateImageDatasetAuditRunRequest(
            dataset_release_id=payload.dataset_release_id,
            image_audit_config=ImageAuditConfig.from_dict(payload.image_audit_config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return ImageDatasetAuditRunResponse.model_validate(dto)


@router.get("/ml/image-audits", response_model=list[ImageDatasetAuditRunResponse])
def list_image_dataset_audit_runs(
    use_case: ListImageDatasetAuditRunsUseCase = Depends(get_list_image_dataset_audit_runs_use_case),
) -> list[ImageDatasetAuditRunResponse]:
    return [ImageDatasetAuditRunResponse.model_validate(dto) for dto in use_case.execute()]


@router.get("/ml/image-audits/{audit_run_id}", response_model=ImageDatasetAuditRunResponse)
def get_image_dataset_audit_run(
    audit_run_id: UUID,
    use_case: GetImageDatasetAuditRunUseCase = Depends(get_get_image_dataset_audit_run_use_case),
) -> ImageDatasetAuditRunResponse:
    return ImageDatasetAuditRunResponse.model_validate(use_case.execute(audit_run_id))


@router.get("/ml/image-audits/{audit_run_id}/issues", response_model=list[ImageDatasetAuditIssueResponse])
def list_image_dataset_audit_issues(
    audit_run_id: UUID,
    use_case: ListImageDatasetAuditIssuesUseCase = Depends(get_list_image_dataset_audit_issues_use_case),
) -> list[ImageDatasetAuditIssueResponse]:
    return [ImageDatasetAuditIssueResponse.model_validate(dto) for dto in use_case.execute(audit_run_id)]


@router.get(
    "/datasets/releases/{dataset_release_id}/image-audits",
    response_model=list[ImageDatasetAuditRunResponse],
)
def list_image_dataset_audit_runs_for_release(
    dataset_release_id: UUID,
    use_case: ListImageDatasetAuditRunsUseCase = Depends(get_list_image_dataset_audit_runs_use_case),
) -> list[ImageDatasetAuditRunResponse]:
    return [
        ImageDatasetAuditRunResponse.model_validate(dto)
        for dto in use_case.execute(dataset_release_id=dataset_release_id)
    ]
