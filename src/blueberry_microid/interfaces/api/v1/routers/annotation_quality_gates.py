from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.annotation_quality_gate_dto import (
    AnnotationQualityGateConfigDTO,
    CreateAnnotationQualityGateRunRequest,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.create_annotation_quality_gate_run import (
    CreateAnnotationQualityGateRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.get_annotation_quality_gate_run import (
    GetAnnotationQualityGateRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.list_annotation_quality_gate_issues import (
    ListAnnotationQualityGateIssuesUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.list_annotation_quality_gate_runs import (
    ListAnnotationQualityGateRunsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_annotation_quality_gate_run_use_case,
    get_get_annotation_quality_gate_run_use_case,
    get_list_annotation_quality_gate_issues_use_case,
    get_list_annotation_quality_gate_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.annotation_quality_gate import (
    AnnotationQualityGateCreate,
    AnnotationQualityGateIssueListResponse,
    AnnotationQualityGateIssueResponse,
    AnnotationQualityGateListResponse,
    AnnotationQualityGateRunResponse,
)

router = APIRouter(tags=["annotation-quality-gates"])


@router.post(
    "/ml/annotation-quality-gates",
    response_model=AnnotationQualityGateRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_annotation_quality_gate(
    payload: AnnotationQualityGateCreate,
    use_case: CreateAnnotationQualityGateRunUseCase = Depends(get_create_annotation_quality_gate_run_use_case),
) -> AnnotationQualityGateRunResponse:
    dto = use_case.execute(
        CreateAnnotationQualityGateRunRequest(
            annotation_bundle_run_id=payload.annotation_bundle_run_id,
            config=AnnotationQualityGateConfigDTO(**payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return AnnotationQualityGateRunResponse.model_validate(dto)


@router.get("/ml/annotation-quality-gates", response_model=AnnotationQualityGateListResponse)
def list_annotation_quality_gates(
    use_case: ListAnnotationQualityGateRunsUseCase = Depends(get_list_annotation_quality_gate_runs_use_case),
) -> AnnotationQualityGateListResponse:
    return AnnotationQualityGateListResponse(
        quality_gates=[AnnotationQualityGateRunResponse.model_validate(dto) for dto in use_case.execute()]
    )


@router.get("/ml/annotation-quality-gates/{quality_gate_run_id}", response_model=AnnotationQualityGateRunResponse)
def get_annotation_quality_gate(
    quality_gate_run_id: UUID,
    use_case: GetAnnotationQualityGateRunUseCase = Depends(get_get_annotation_quality_gate_run_use_case),
) -> AnnotationQualityGateRunResponse:
    return AnnotationQualityGateRunResponse.model_validate(use_case.execute(quality_gate_run_id))


@router.get(
    "/ml/annotation-quality-gates/{quality_gate_run_id}/issues",
    response_model=AnnotationQualityGateIssueListResponse,
)
def list_annotation_quality_gate_issues(
    quality_gate_run_id: UUID,
    use_case: ListAnnotationQualityGateIssuesUseCase = Depends(get_list_annotation_quality_gate_issues_use_case),
) -> AnnotationQualityGateIssueListResponse:
    return AnnotationQualityGateIssueListResponse(
        issues=[AnnotationQualityGateIssueResponse.model_validate(dto) for dto in use_case.execute(quality_gate_run_id)]
    )


@router.get(
    "/datasets/releases/{dataset_release_id}/annotation-quality-gates",
    response_model=AnnotationQualityGateListResponse,
)
def list_annotation_quality_gates_for_release(
    dataset_release_id: UUID,
    use_case: ListAnnotationQualityGateRunsUseCase = Depends(get_list_annotation_quality_gate_runs_use_case),
) -> AnnotationQualityGateListResponse:
    return AnnotationQualityGateListResponse(
        quality_gates=[
            AnnotationQualityGateRunResponse.model_validate(dto)
            for dto in use_case.execute(dataset_release_id=dataset_release_id)
        ]
    )


@router.get(
    "/ml/annotation-bundles/{annotation_bundle_run_id}/quality-gates",
    response_model=AnnotationQualityGateListResponse,
)
def list_annotation_quality_gates_for_bundle(
    annotation_bundle_run_id: UUID,
    use_case: ListAnnotationQualityGateRunsUseCase = Depends(get_list_annotation_quality_gate_runs_use_case),
) -> AnnotationQualityGateListResponse:
    return AnnotationQualityGateListResponse(
        quality_gates=[
            AnnotationQualityGateRunResponse.model_validate(dto)
            for dto in use_case.execute(annotation_bundle_run_id=annotation_bundle_run_id)
        ]
    )
