from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.ml_preflight_dto import CreateTrainingPreflightRunRequest
from blueberry_microid.application.use_cases.ml_preflight.create_training_preflight_run import (
    CreateTrainingPreflightRunUseCase,
)
from blueberry_microid.application.use_cases.ml_preflight.get_training_preflight_run import (
    GetTrainingPreflightRunUseCase,
)
from blueberry_microid.application.use_cases.ml_preflight.list_training_preflight_issues import (
    ListTrainingPreflightIssuesUseCase,
)
from blueberry_microid.application.use_cases.ml_preflight.list_training_preflight_runs import (
    ListTrainingPreflightRunsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_training_preflight_run_use_case,
    get_get_training_preflight_run_use_case,
    get_list_training_preflight_issues_use_case,
    get_list_training_preflight_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.ml_preflight import (
    CreateTrainingPreflightRunRequestBody,
    TrainingPreflightIssueResponse,
    TrainingPreflightRunResponse,
)
from blueberry_microid.ml.configs.training_config import TrainingConfig

router = APIRouter(prefix="/ml/preflight-runs", tags=["ml-preflight"])


@router.post("", response_model=TrainingPreflightRunResponse, status_code=status.HTTP_201_CREATED)
def create_training_preflight_run(
    payload: CreateTrainingPreflightRunRequestBody,
    use_case: CreateTrainingPreflightRunUseCase = Depends(get_create_training_preflight_run_use_case),
) -> TrainingPreflightRunResponse:
    dto = use_case.execute(
        CreateTrainingPreflightRunRequest(
            dataset_release_id=payload.dataset_release_id,
            training_config=TrainingConfig.from_dict(payload.training_config.model_dump()),
            validate_image_paths=payload.validate_image_paths,
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return TrainingPreflightRunResponse.model_validate(dto)


@router.get("", response_model=list[TrainingPreflightRunResponse])
def list_training_preflight_runs(
    use_case: ListTrainingPreflightRunsUseCase = Depends(get_list_training_preflight_runs_use_case),
) -> list[TrainingPreflightRunResponse]:
    return [TrainingPreflightRunResponse.model_validate(dto) for dto in use_case.execute()]


@router.get("/{preflight_run_id}", response_model=TrainingPreflightRunResponse)
def get_training_preflight_run(
    preflight_run_id: UUID,
    use_case: GetTrainingPreflightRunUseCase = Depends(get_get_training_preflight_run_use_case),
) -> TrainingPreflightRunResponse:
    return TrainingPreflightRunResponse.model_validate(use_case.execute(preflight_run_id))


@router.get("/{preflight_run_id}/issues", response_model=list[TrainingPreflightIssueResponse])
def list_training_preflight_issues(
    preflight_run_id: UUID,
    use_case: ListTrainingPreflightIssuesUseCase = Depends(get_list_training_preflight_issues_use_case),
) -> list[TrainingPreflightIssueResponse]:
    return [TrainingPreflightIssueResponse.model_validate(dto) for dto in use_case.execute(preflight_run_id)]
