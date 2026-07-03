from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.detection_training_readiness_dto import (
    CreateDetectionTrainingReadinessReportRequest,
    DetectionTrainingReadinessConfigDTO,
)
from blueberry_microid.application.use_cases.detection_training_readiness.create_detection_training_readiness_report import (
    CreateDetectionTrainingReadinessReportUseCase,
)
from blueberry_microid.application.use_cases.detection_training_readiness.get_detection_training_readiness_report import (
    GetDetectionTrainingReadinessReportUseCase,
)
from blueberry_microid.application.use_cases.detection_training_readiness.list_detection_training_readiness_issues import (
    ListDetectionTrainingReadinessIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_readiness.list_detection_training_readiness_reports import (
    ListDetectionTrainingReadinessReportsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_detection_training_readiness_report_use_case,
    get_get_detection_training_readiness_report_use_case,
    get_list_detection_training_readiness_issues_use_case,
    get_list_detection_training_readiness_reports_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.detection_training_readiness import (
    CreateDetectionTrainingReadinessReportRequestBody,
    DetectionTrainingReadinessIssueListResponse,
    DetectionTrainingReadinessIssueResponse,
    DetectionTrainingReadinessReportListResponse,
    DetectionTrainingReadinessReportResponse,
)

router = APIRouter(tags=["detection-training-readiness"])


@router.post(
    "/ml/detection-training-readiness-reports",
    response_model=DetectionTrainingReadinessReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_detection_training_readiness_report(
    payload: CreateDetectionTrainingReadinessReportRequestBody,
    use_case: CreateDetectionTrainingReadinessReportUseCase = Depends(
        get_create_detection_training_readiness_report_use_case
    ),
) -> DetectionTrainingReadinessReportResponse:
    dto = use_case.execute(
        CreateDetectionTrainingReadinessReportRequest(
            detection_training_run_id=payload.detection_training_run_id,
            config=DetectionTrainingReadinessConfigDTO(**payload.config.model_dump()),
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return DetectionTrainingReadinessReportResponse.model_validate(dto)


@router.get("/ml/detection-training-readiness-reports", response_model=DetectionTrainingReadinessReportListResponse)
def list_detection_training_readiness_reports(
    use_case: ListDetectionTrainingReadinessReportsUseCase = Depends(
        get_list_detection_training_readiness_reports_use_case
    ),
) -> DetectionTrainingReadinessReportListResponse:
    return DetectionTrainingReadinessReportListResponse(
        readiness_reports=[DetectionTrainingReadinessReportResponse.model_validate(dto) for dto in use_case.execute()]
    )


@router.get(
    "/ml/detection-training-readiness-reports/{readiness_report_id}",
    response_model=DetectionTrainingReadinessReportResponse,
)
def get_detection_training_readiness_report(
    readiness_report_id: UUID,
    use_case: GetDetectionTrainingReadinessReportUseCase = Depends(
        get_get_detection_training_readiness_report_use_case
    ),
) -> DetectionTrainingReadinessReportResponse:
    return DetectionTrainingReadinessReportResponse.model_validate(use_case.execute(readiness_report_id))


@router.get(
    "/ml/detection-training-readiness-reports/{readiness_report_id}/issues",
    response_model=DetectionTrainingReadinessIssueListResponse,
)
def list_detection_training_readiness_issues(
    readiness_report_id: UUID,
    use_case: ListDetectionTrainingReadinessIssuesUseCase = Depends(
        get_list_detection_training_readiness_issues_use_case
    ),
) -> DetectionTrainingReadinessIssueListResponse:
    return DetectionTrainingReadinessIssueListResponse(
        issues=[
            DetectionTrainingReadinessIssueResponse.model_validate(dto)
            for dto in use_case.execute(readiness_report_id)
        ]
    )


@router.get(
    "/ml/detection-training-runs/{detection_training_run_id}/readiness-reports",
    response_model=DetectionTrainingReadinessReportListResponse,
)
def list_detection_training_readiness_reports_for_run(
    detection_training_run_id: UUID,
    use_case: ListDetectionTrainingReadinessReportsUseCase = Depends(
        get_list_detection_training_readiness_reports_use_case
    ),
) -> DetectionTrainingReadinessReportListResponse:
    return DetectionTrainingReadinessReportListResponse(
        readiness_reports=[
            DetectionTrainingReadinessReportResponse.model_validate(dto)
            for dto in use_case.execute(detection_training_run_id=detection_training_run_id)
        ]
    )


@router.get(
    "/datasets/releases/{dataset_release_id}/detection-training-readiness-reports",
    response_model=DetectionTrainingReadinessReportListResponse,
)
def list_detection_training_readiness_reports_for_release(
    dataset_release_id: UUID,
    use_case: ListDetectionTrainingReadinessReportsUseCase = Depends(
        get_list_detection_training_readiness_reports_use_case
    ),
) -> DetectionTrainingReadinessReportListResponse:
    return DetectionTrainingReadinessReportListResponse(
        readiness_reports=[
            DetectionTrainingReadinessReportResponse.model_validate(dto)
            for dto in use_case.execute(dataset_release_id=dataset_release_id)
        ]
    )


@router.get(
    "/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-readiness-reports",
    response_model=DetectionTrainingReadinessReportListResponse,
)
def list_detection_training_readiness_reports_for_bundle(
    annotation_bundle_run_id: UUID,
    use_case: ListDetectionTrainingReadinessReportsUseCase = Depends(
        get_list_detection_training_readiness_reports_use_case
    ),
) -> DetectionTrainingReadinessReportListResponse:
    return DetectionTrainingReadinessReportListResponse(
        readiness_reports=[
            DetectionTrainingReadinessReportResponse.model_validate(dto)
            for dto in use_case.execute(annotation_bundle_run_id=annotation_bundle_run_id)
        ]
    )


@router.get(
    "/ml/annotation-quality-gates/{annotation_quality_gate_run_id}/detection-training-readiness-reports",
    response_model=DetectionTrainingReadinessReportListResponse,
)
def list_detection_training_readiness_reports_for_quality_gate(
    annotation_quality_gate_run_id: UUID,
    use_case: ListDetectionTrainingReadinessReportsUseCase = Depends(
        get_list_detection_training_readiness_reports_use_case
    ),
) -> DetectionTrainingReadinessReportListResponse:
    return DetectionTrainingReadinessReportListResponse(
        readiness_reports=[
            DetectionTrainingReadinessReportResponse.model_validate(dto)
            for dto in use_case.execute(annotation_quality_gate_run_id=annotation_quality_gate_run_id)
        ]
    )
