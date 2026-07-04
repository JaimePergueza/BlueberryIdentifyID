from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.detection_training_execution_dto import (
    CreateDetectionTrainingExecutionRunRequest,
    DetectionTrainingExecutionConfigDTO,
)
from blueberry_microid.application.use_cases.detection_training_execution.create_detection_training_execution_run import (
    CreateDetectionTrainingExecutionRunUseCase,
)
from blueberry_microid.application.use_cases.detection_training_execution.get_detection_training_execution_run import (
    GetDetectionTrainingExecutionRunUseCase,
)
from blueberry_microid.application.use_cases.detection_training_execution.list_detection_training_execution_issues import (
    ListDetectionTrainingExecutionIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_execution.list_detection_training_execution_runs import (
    ListDetectionTrainingExecutionRunsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_detection_training_execution_run_use_case,
    get_get_detection_training_execution_run_use_case,
    get_list_detection_training_execution_issues_use_case,
    get_list_detection_training_execution_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.detection_training_execution import (
    CreateDetectionTrainingExecutionRunRequestBody,
    DetectionTrainingExecutionIssueListResponse,
    DetectionTrainingExecutionIssueResponse,
    DetectionTrainingExecutionRunListResponse,
    DetectionTrainingExecutionRunResponse,
)

router = APIRouter(tags=["detection-training-execution"])


@router.post(
    "/ml/detection-training-execution-runs",
    response_model=DetectionTrainingExecutionRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_detection_training_execution_run(
    payload: CreateDetectionTrainingExecutionRunRequestBody,
    use_case: CreateDetectionTrainingExecutionRunUseCase = Depends(
        get_create_detection_training_execution_run_use_case
    ),
) -> DetectionTrainingExecutionRunResponse:
    dto = use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=payload.detection_training_run_id,
            readiness_report_id=payload.readiness_report_id,
            environment_spec_id=payload.environment_spec_id,
            artifact_policy_id=payload.artifact_policy_id,
            config=DetectionTrainingExecutionConfigDTO(**payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return DetectionTrainingExecutionRunResponse.model_validate(dto)


@router.get(
    "/ml/detection-training-execution-runs", response_model=DetectionTrainingExecutionRunListResponse
)
def list_detection_training_execution_runs(
    use_case: ListDetectionTrainingExecutionRunsUseCase = Depends(
        get_list_detection_training_execution_runs_use_case
    ),
) -> DetectionTrainingExecutionRunListResponse:
    return DetectionTrainingExecutionRunListResponse(
        execution_runs=[
            DetectionTrainingExecutionRunResponse.model_validate(dto) for dto in use_case.execute()
        ]
    )


@router.get(
    "/ml/detection-training-execution-runs/{execution_run_id}",
    response_model=DetectionTrainingExecutionRunResponse,
)
def get_detection_training_execution_run(
    execution_run_id: UUID,
    use_case: GetDetectionTrainingExecutionRunUseCase = Depends(get_get_detection_training_execution_run_use_case),
) -> DetectionTrainingExecutionRunResponse:
    return DetectionTrainingExecutionRunResponse.model_validate(use_case.execute(execution_run_id))


@router.get(
    "/ml/detection-training-execution-runs/{execution_run_id}/issues",
    response_model=DetectionTrainingExecutionIssueListResponse,
)
def list_detection_training_execution_issues(
    execution_run_id: UUID,
    use_case: ListDetectionTrainingExecutionIssuesUseCase = Depends(
        get_list_detection_training_execution_issues_use_case
    ),
) -> DetectionTrainingExecutionIssueListResponse:
    return DetectionTrainingExecutionIssueListResponse(
        issues=[
            DetectionTrainingExecutionIssueResponse.model_validate(dto)
            for dto in use_case.execute(execution_run_id)
        ]
    )


@router.get(
    "/ml/detection-training-runs/{detection_training_run_id}/execution-runs",
    response_model=DetectionTrainingExecutionRunListResponse,
)
def list_detection_training_execution_runs_for_run(
    detection_training_run_id: UUID,
    use_case: ListDetectionTrainingExecutionRunsUseCase = Depends(
        get_list_detection_training_execution_runs_use_case
    ),
) -> DetectionTrainingExecutionRunListResponse:
    return DetectionTrainingExecutionRunListResponse(
        execution_runs=[
            DetectionTrainingExecutionRunResponse.model_validate(dto)
            for dto in use_case.execute(detection_training_run_id=detection_training_run_id)
        ]
    )


@router.get(
    "/ml/detection-training-readiness-reports/{readiness_report_id}/execution-runs",
    response_model=DetectionTrainingExecutionRunListResponse,
)
def list_detection_training_execution_runs_for_readiness_report(
    readiness_report_id: UUID,
    use_case: ListDetectionTrainingExecutionRunsUseCase = Depends(
        get_list_detection_training_execution_runs_use_case
    ),
) -> DetectionTrainingExecutionRunListResponse:
    return DetectionTrainingExecutionRunListResponse(
        execution_runs=[
            DetectionTrainingExecutionRunResponse.model_validate(dto)
            for dto in use_case.execute(readiness_report_id=readiness_report_id)
        ]
    )


@router.get(
    "/ml/detection-training-environment-specs/{environment_spec_id}/execution-runs",
    response_model=DetectionTrainingExecutionRunListResponse,
)
def list_detection_training_execution_runs_for_environment_spec(
    environment_spec_id: UUID,
    use_case: ListDetectionTrainingExecutionRunsUseCase = Depends(
        get_list_detection_training_execution_runs_use_case
    ),
) -> DetectionTrainingExecutionRunListResponse:
    return DetectionTrainingExecutionRunListResponse(
        execution_runs=[
            DetectionTrainingExecutionRunResponse.model_validate(dto)
            for dto in use_case.execute(environment_spec_id=environment_spec_id)
        ]
    )


@router.get(
    "/ml/detection-training-artifact-policies/{artifact_policy_id}/execution-runs",
    response_model=DetectionTrainingExecutionRunListResponse,
)
def list_detection_training_execution_runs_for_artifact_policy(
    artifact_policy_id: UUID,
    use_case: ListDetectionTrainingExecutionRunsUseCase = Depends(
        get_list_detection_training_execution_runs_use_case
    ),
) -> DetectionTrainingExecutionRunListResponse:
    return DetectionTrainingExecutionRunListResponse(
        execution_runs=[
            DetectionTrainingExecutionRunResponse.model_validate(dto)
            for dto in use_case.execute(artifact_policy_id=artifact_policy_id)
        ]
    )


@router.get(
    "/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-execution-runs",
    response_model=DetectionTrainingExecutionRunListResponse,
)
def list_detection_training_execution_runs_for_bundle(
    annotation_bundle_run_id: UUID,
    use_case: ListDetectionTrainingExecutionRunsUseCase = Depends(
        get_list_detection_training_execution_runs_use_case
    ),
) -> DetectionTrainingExecutionRunListResponse:
    return DetectionTrainingExecutionRunListResponse(
        execution_runs=[
            DetectionTrainingExecutionRunResponse.model_validate(dto)
            for dto in use_case.execute(annotation_bundle_run_id=annotation_bundle_run_id)
        ]
    )


@router.get(
    "/datasets/releases/{dataset_release_id}/detection-training-execution-runs",
    response_model=DetectionTrainingExecutionRunListResponse,
)
def list_detection_training_execution_runs_for_release(
    dataset_release_id: UUID,
    use_case: ListDetectionTrainingExecutionRunsUseCase = Depends(
        get_list_detection_training_execution_runs_use_case
    ),
) -> DetectionTrainingExecutionRunListResponse:
    return DetectionTrainingExecutionRunListResponse(
        execution_runs=[
            DetectionTrainingExecutionRunResponse.model_validate(dto)
            for dto in use_case.execute(dataset_release_id=dataset_release_id)
        ]
    )
