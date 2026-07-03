from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.detection_training_environment_dto import (
    CreateDetectionTrainingEnvironmentSpecRequest,
    DetectionTrainingEnvironmentConfigDTO,
)
from blueberry_microid.application.use_cases.detection_training_environment.create_detection_training_environment_spec import (
    CreateDetectionTrainingEnvironmentSpecUseCase,
)
from blueberry_microid.application.use_cases.detection_training_environment.get_detection_training_environment_spec import (
    GetDetectionTrainingEnvironmentSpecUseCase,
)
from blueberry_microid.application.use_cases.detection_training_environment.list_detection_training_environment_issues import (
    ListDetectionTrainingEnvironmentIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_environment.list_detection_training_environment_specs import (
    ListDetectionTrainingEnvironmentSpecsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_detection_training_environment_spec_use_case,
    get_get_detection_training_environment_spec_use_case,
    get_list_detection_training_environment_issues_use_case,
    get_list_detection_training_environment_specs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.detection_training_environment import (
    CreateDetectionTrainingEnvironmentSpecRequestBody,
    DetectionTrainingEnvironmentIssueListResponse,
    DetectionTrainingEnvironmentIssueResponse,
    DetectionTrainingEnvironmentSpecListResponse,
    DetectionTrainingEnvironmentSpecResponse,
)

router = APIRouter(tags=["detection-training-environment"])


@router.post(
    "/ml/detection-training-environment-specs",
    response_model=DetectionTrainingEnvironmentSpecResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_detection_training_environment_spec(
    payload: CreateDetectionTrainingEnvironmentSpecRequestBody,
    use_case: CreateDetectionTrainingEnvironmentSpecUseCase = Depends(
        get_create_detection_training_environment_spec_use_case
    ),
) -> DetectionTrainingEnvironmentSpecResponse:
    dto = use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=payload.detection_training_run_id,
            readiness_report_id=payload.readiness_report_id,
            config=DetectionTrainingEnvironmentConfigDTO(**payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return DetectionTrainingEnvironmentSpecResponse.model_validate(dto)


@router.get("/ml/detection-training-environment-specs", response_model=DetectionTrainingEnvironmentSpecListResponse)
def list_detection_training_environment_specs(
    use_case: ListDetectionTrainingEnvironmentSpecsUseCase = Depends(
        get_list_detection_training_environment_specs_use_case
    ),
) -> DetectionTrainingEnvironmentSpecListResponse:
    return DetectionTrainingEnvironmentSpecListResponse(
        environment_specs=[
            DetectionTrainingEnvironmentSpecResponse.model_validate(dto) for dto in use_case.execute()
        ]
    )


@router.get(
    "/ml/detection-training-environment-specs/{environment_spec_id}",
    response_model=DetectionTrainingEnvironmentSpecResponse,
)
def get_detection_training_environment_spec(
    environment_spec_id: UUID,
    use_case: GetDetectionTrainingEnvironmentSpecUseCase = Depends(
        get_get_detection_training_environment_spec_use_case
    ),
) -> DetectionTrainingEnvironmentSpecResponse:
    return DetectionTrainingEnvironmentSpecResponse.model_validate(use_case.execute(environment_spec_id))


@router.get(
    "/ml/detection-training-environment-specs/{environment_spec_id}/issues",
    response_model=DetectionTrainingEnvironmentIssueListResponse,
)
def list_detection_training_environment_issues(
    environment_spec_id: UUID,
    use_case: ListDetectionTrainingEnvironmentIssuesUseCase = Depends(
        get_list_detection_training_environment_issues_use_case
    ),
) -> DetectionTrainingEnvironmentIssueListResponse:
    return DetectionTrainingEnvironmentIssueListResponse(
        issues=[
            DetectionTrainingEnvironmentIssueResponse.model_validate(dto)
            for dto in use_case.execute(environment_spec_id)
        ]
    )


@router.get(
    "/ml/detection-training-runs/{detection_training_run_id}/environment-specs",
    response_model=DetectionTrainingEnvironmentSpecListResponse,
)
def list_detection_training_environment_specs_for_run(
    detection_training_run_id: UUID,
    use_case: ListDetectionTrainingEnvironmentSpecsUseCase = Depends(
        get_list_detection_training_environment_specs_use_case
    ),
) -> DetectionTrainingEnvironmentSpecListResponse:
    return DetectionTrainingEnvironmentSpecListResponse(
        environment_specs=[
            DetectionTrainingEnvironmentSpecResponse.model_validate(dto)
            for dto in use_case.execute(detection_training_run_id=detection_training_run_id)
        ]
    )


@router.get(
    "/ml/detection-training-readiness-reports/{readiness_report_id}/environment-specs",
    response_model=DetectionTrainingEnvironmentSpecListResponse,
)
def list_detection_training_environment_specs_for_readiness_report(
    readiness_report_id: UUID,
    use_case: ListDetectionTrainingEnvironmentSpecsUseCase = Depends(
        get_list_detection_training_environment_specs_use_case
    ),
) -> DetectionTrainingEnvironmentSpecListResponse:
    return DetectionTrainingEnvironmentSpecListResponse(
        environment_specs=[
            DetectionTrainingEnvironmentSpecResponse.model_validate(dto)
            for dto in use_case.execute(readiness_report_id=readiness_report_id)
        ]
    )


@router.get(
    "/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-environment-specs",
    response_model=DetectionTrainingEnvironmentSpecListResponse,
)
def list_detection_training_environment_specs_for_bundle(
    annotation_bundle_run_id: UUID,
    use_case: ListDetectionTrainingEnvironmentSpecsUseCase = Depends(
        get_list_detection_training_environment_specs_use_case
    ),
) -> DetectionTrainingEnvironmentSpecListResponse:
    return DetectionTrainingEnvironmentSpecListResponse(
        environment_specs=[
            DetectionTrainingEnvironmentSpecResponse.model_validate(dto)
            for dto in use_case.execute(annotation_bundle_run_id=annotation_bundle_run_id)
        ]
    )


@router.get(
    "/datasets/releases/{dataset_release_id}/detection-training-environment-specs",
    response_model=DetectionTrainingEnvironmentSpecListResponse,
)
def list_detection_training_environment_specs_for_release(
    dataset_release_id: UUID,
    use_case: ListDetectionTrainingEnvironmentSpecsUseCase = Depends(
        get_list_detection_training_environment_specs_use_case
    ),
) -> DetectionTrainingEnvironmentSpecListResponse:
    return DetectionTrainingEnvironmentSpecListResponse(
        environment_specs=[
            DetectionTrainingEnvironmentSpecResponse.model_validate(dto)
            for dto in use_case.execute(dataset_release_id=dataset_release_id)
        ]
    )
