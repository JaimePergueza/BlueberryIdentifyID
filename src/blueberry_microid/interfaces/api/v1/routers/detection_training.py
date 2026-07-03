from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.detection_training_dto import (
    CreateDetectionTrainingRunRequest,
    DetectionTrainingConfigDTO,
)
from blueberry_microid.application.use_cases.detection_training.create_detection_training_run import (
    CreateDetectionTrainingRunUseCase,
)
from blueberry_microid.application.use_cases.detection_training.get_detection_training_run import (
    GetDetectionTrainingRunUseCase,
)
from blueberry_microid.application.use_cases.detection_training.list_detection_training_issues import (
    ListDetectionTrainingIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training.list_detection_training_runs import (
    ListDetectionTrainingRunsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_detection_training_run_use_case,
    get_get_detection_training_run_use_case,
    get_list_detection_training_issues_use_case,
    get_list_detection_training_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.detection_training import (
    CreateDetectionTrainingRunRequestBody,
    DetectionTrainingIssueListResponse,
    DetectionTrainingIssueResponse,
    DetectionTrainingRunListResponse,
    DetectionTrainingRunResponse,
)

router = APIRouter(tags=["detection-training"])


@router.post(
    "/ml/detection-training-runs",
    response_model=DetectionTrainingRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_detection_training_run(
    payload: CreateDetectionTrainingRunRequestBody,
    use_case: CreateDetectionTrainingRunUseCase = Depends(get_create_detection_training_run_use_case),
) -> DetectionTrainingRunResponse:
    dto = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=payload.annotation_bundle_run_id,
            annotation_quality_gate_run_id=payload.annotation_quality_gate_run_id,
            config=DetectionTrainingConfigDTO(**payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return DetectionTrainingRunResponse.model_validate(dto)


@router.get("/ml/detection-training-runs", response_model=DetectionTrainingRunListResponse)
def list_detection_training_runs(
    use_case: ListDetectionTrainingRunsUseCase = Depends(get_list_detection_training_runs_use_case),
) -> DetectionTrainingRunListResponse:
    return DetectionTrainingRunListResponse(
        detection_training_runs=[DetectionTrainingRunResponse.model_validate(dto) for dto in use_case.execute()]
    )


@router.get("/ml/detection-training-runs/{detection_training_run_id}", response_model=DetectionTrainingRunResponse)
def get_detection_training_run(
    detection_training_run_id: UUID,
    use_case: GetDetectionTrainingRunUseCase = Depends(get_get_detection_training_run_use_case),
) -> DetectionTrainingRunResponse:
    return DetectionTrainingRunResponse.model_validate(use_case.execute(detection_training_run_id))


@router.get(
    "/ml/detection-training-runs/{detection_training_run_id}/issues",
    response_model=DetectionTrainingIssueListResponse,
)
def list_detection_training_issues(
    detection_training_run_id: UUID,
    use_case: ListDetectionTrainingIssuesUseCase = Depends(get_list_detection_training_issues_use_case),
) -> DetectionTrainingIssueListResponse:
    return DetectionTrainingIssueListResponse(
        issues=[
            DetectionTrainingIssueResponse.model_validate(dto)
            for dto in use_case.execute(detection_training_run_id)
        ]
    )


@router.get(
    "/datasets/releases/{dataset_release_id}/detection-training-runs",
    response_model=DetectionTrainingRunListResponse,
)
def list_detection_training_runs_for_release(
    dataset_release_id: UUID,
    use_case: ListDetectionTrainingRunsUseCase = Depends(get_list_detection_training_runs_use_case),
) -> DetectionTrainingRunListResponse:
    return DetectionTrainingRunListResponse(
        detection_training_runs=[
            DetectionTrainingRunResponse.model_validate(dto)
            for dto in use_case.execute(dataset_release_id=dataset_release_id)
        ]
    )


@router.get(
    "/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-runs",
    response_model=DetectionTrainingRunListResponse,
)
def list_detection_training_runs_for_bundle(
    annotation_bundle_run_id: UUID,
    use_case: ListDetectionTrainingRunsUseCase = Depends(get_list_detection_training_runs_use_case),
) -> DetectionTrainingRunListResponse:
    return DetectionTrainingRunListResponse(
        detection_training_runs=[
            DetectionTrainingRunResponse.model_validate(dto)
            for dto in use_case.execute(annotation_bundle_run_id=annotation_bundle_run_id)
        ]
    )


@router.get(
    "/ml/annotation-quality-gates/{quality_gate_run_id}/detection-training-runs",
    response_model=DetectionTrainingRunListResponse,
)
def list_detection_training_runs_for_quality_gate(
    quality_gate_run_id: UUID,
    use_case: ListDetectionTrainingRunsUseCase = Depends(get_list_detection_training_runs_use_case),
) -> DetectionTrainingRunListResponse:
    return DetectionTrainingRunListResponse(
        detection_training_runs=[
            DetectionTrainingRunResponse.model_validate(dto)
            for dto in use_case.execute(annotation_quality_gate_run_id=quality_gate_run_id)
        ]
    )
