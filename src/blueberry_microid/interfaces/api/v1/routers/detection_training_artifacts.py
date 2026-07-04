from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.detection_training_artifact_dto import (
    CreateDetectionTrainingArtifactPolicyRequest,
    DetectionTrainingArtifactPolicyConfigDTO,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.create_detection_training_artifact_policy import (
    CreateDetectionTrainingArtifactPolicyUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.get_detection_training_artifact_policy import (
    GetDetectionTrainingArtifactPolicyUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.list_detection_training_artifact_issues import (
    ListDetectionTrainingArtifactIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.list_detection_training_artifact_policies import (
    ListDetectionTrainingArtifactPoliciesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.list_detection_training_artifact_records import (
    ListDetectionTrainingArtifactRecordsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_detection_training_artifact_policy_use_case,
    get_get_detection_training_artifact_policy_use_case,
    get_list_detection_training_artifact_issues_use_case,
    get_list_detection_training_artifact_policies_use_case,
    get_list_detection_training_artifact_records_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.detection_training_artifacts import (
    CreateDetectionTrainingArtifactPolicyRequestBody,
    DetectionTrainingArtifactIssueListResponse,
    DetectionTrainingArtifactIssueResponse,
    DetectionTrainingArtifactPolicyListResponse,
    DetectionTrainingArtifactPolicyResponse,
    DetectionTrainingArtifactRecordListResponse,
    DetectionTrainingArtifactRecordResponse,
)

router = APIRouter(tags=["detection-training-artifacts"])


@router.post(
    "/ml/detection-training-artifact-policies",
    response_model=DetectionTrainingArtifactPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_detection_training_artifact_policy(
    payload: CreateDetectionTrainingArtifactPolicyRequestBody,
    use_case: CreateDetectionTrainingArtifactPolicyUseCase = Depends(
        get_create_detection_training_artifact_policy_use_case
    ),
) -> DetectionTrainingArtifactPolicyResponse:
    dto = use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=payload.detection_training_run_id,
            readiness_report_id=payload.readiness_report_id,
            environment_spec_id=payload.environment_spec_id,
            config=DetectionTrainingArtifactPolicyConfigDTO(**payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return DetectionTrainingArtifactPolicyResponse.model_validate(dto)


@router.get(
    "/ml/detection-training-artifact-policies", response_model=DetectionTrainingArtifactPolicyListResponse
)
def list_detection_training_artifact_policies(
    use_case: ListDetectionTrainingArtifactPoliciesUseCase = Depends(
        get_list_detection_training_artifact_policies_use_case
    ),
) -> DetectionTrainingArtifactPolicyListResponse:
    return DetectionTrainingArtifactPolicyListResponse(
        artifact_policies=[
            DetectionTrainingArtifactPolicyResponse.model_validate(dto) for dto in use_case.execute()
        ]
    )


@router.get(
    "/ml/detection-training-artifact-policies/{artifact_policy_id}",
    response_model=DetectionTrainingArtifactPolicyResponse,
)
def get_detection_training_artifact_policy(
    artifact_policy_id: UUID,
    use_case: GetDetectionTrainingArtifactPolicyUseCase = Depends(
        get_get_detection_training_artifact_policy_use_case
    ),
) -> DetectionTrainingArtifactPolicyResponse:
    return DetectionTrainingArtifactPolicyResponse.model_validate(use_case.execute(artifact_policy_id))


@router.get(
    "/ml/detection-training-artifact-policies/{artifact_policy_id}/records",
    response_model=DetectionTrainingArtifactRecordListResponse,
)
def list_detection_training_artifact_records(
    artifact_policy_id: UUID,
    use_case: ListDetectionTrainingArtifactRecordsUseCase = Depends(
        get_list_detection_training_artifact_records_use_case
    ),
) -> DetectionTrainingArtifactRecordListResponse:
    return DetectionTrainingArtifactRecordListResponse(
        records=[
            DetectionTrainingArtifactRecordResponse.model_validate(dto)
            for dto in use_case.execute(artifact_policy_id)
        ]
    )


@router.get(
    "/ml/detection-training-artifact-policies/{artifact_policy_id}/issues",
    response_model=DetectionTrainingArtifactIssueListResponse,
)
def list_detection_training_artifact_issues(
    artifact_policy_id: UUID,
    use_case: ListDetectionTrainingArtifactIssuesUseCase = Depends(
        get_list_detection_training_artifact_issues_use_case
    ),
) -> DetectionTrainingArtifactIssueListResponse:
    return DetectionTrainingArtifactIssueListResponse(
        issues=[
            DetectionTrainingArtifactIssueResponse.model_validate(dto)
            for dto in use_case.execute(artifact_policy_id)
        ]
    )


@router.get(
    "/ml/detection-training-runs/{detection_training_run_id}/artifact-policies",
    response_model=DetectionTrainingArtifactPolicyListResponse,
)
def list_detection_training_artifact_policies_for_run(
    detection_training_run_id: UUID,
    use_case: ListDetectionTrainingArtifactPoliciesUseCase = Depends(
        get_list_detection_training_artifact_policies_use_case
    ),
) -> DetectionTrainingArtifactPolicyListResponse:
    return DetectionTrainingArtifactPolicyListResponse(
        artifact_policies=[
            DetectionTrainingArtifactPolicyResponse.model_validate(dto)
            for dto in use_case.execute(detection_training_run_id=detection_training_run_id)
        ]
    )


@router.get(
    "/ml/detection-training-readiness-reports/{readiness_report_id}/artifact-policies",
    response_model=DetectionTrainingArtifactPolicyListResponse,
)
def list_detection_training_artifact_policies_for_readiness_report(
    readiness_report_id: UUID,
    use_case: ListDetectionTrainingArtifactPoliciesUseCase = Depends(
        get_list_detection_training_artifact_policies_use_case
    ),
) -> DetectionTrainingArtifactPolicyListResponse:
    return DetectionTrainingArtifactPolicyListResponse(
        artifact_policies=[
            DetectionTrainingArtifactPolicyResponse.model_validate(dto)
            for dto in use_case.execute(readiness_report_id=readiness_report_id)
        ]
    )


@router.get(
    "/ml/detection-training-environment-specs/{environment_spec_id}/artifact-policies",
    response_model=DetectionTrainingArtifactPolicyListResponse,
)
def list_detection_training_artifact_policies_for_environment_spec(
    environment_spec_id: UUID,
    use_case: ListDetectionTrainingArtifactPoliciesUseCase = Depends(
        get_list_detection_training_artifact_policies_use_case
    ),
) -> DetectionTrainingArtifactPolicyListResponse:
    return DetectionTrainingArtifactPolicyListResponse(
        artifact_policies=[
            DetectionTrainingArtifactPolicyResponse.model_validate(dto)
            for dto in use_case.execute(environment_spec_id=environment_spec_id)
        ]
    )


@router.get(
    "/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-artifact-policies",
    response_model=DetectionTrainingArtifactPolicyListResponse,
)
def list_detection_training_artifact_policies_for_bundle(
    annotation_bundle_run_id: UUID,
    use_case: ListDetectionTrainingArtifactPoliciesUseCase = Depends(
        get_list_detection_training_artifact_policies_use_case
    ),
) -> DetectionTrainingArtifactPolicyListResponse:
    return DetectionTrainingArtifactPolicyListResponse(
        artifact_policies=[
            DetectionTrainingArtifactPolicyResponse.model_validate(dto)
            for dto in use_case.execute(annotation_bundle_run_id=annotation_bundle_run_id)
        ]
    )


@router.get(
    "/datasets/releases/{dataset_release_id}/detection-training-artifact-policies",
    response_model=DetectionTrainingArtifactPolicyListResponse,
)
def list_detection_training_artifact_policies_for_release(
    dataset_release_id: UUID,
    use_case: ListDetectionTrainingArtifactPoliciesUseCase = Depends(
        get_list_detection_training_artifact_policies_use_case
    ),
) -> DetectionTrainingArtifactPolicyListResponse:
    return DetectionTrainingArtifactPolicyListResponse(
        artifact_policies=[
            DetectionTrainingArtifactPolicyResponse.model_validate(dto)
            for dto in use_case.execute(dataset_release_id=dataset_release_id)
        ]
    )
