from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from blueberry_microid.application.dto.training_run_dto import CreateBaselineTrainingRunRequest
from blueberry_microid.application.use_cases.training.create_baseline_training_run import CreateBaselineTrainingRunUseCase
from blueberry_microid.application.use_cases.training.get_training_run import GetTrainingRunUseCase
from blueberry_microid.application.use_cases.training.list_training_predictions import ListTrainingPredictionsUseCase
from blueberry_microid.application.use_cases.training.list_training_runs import ListTrainingRunsUseCase
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_baseline_training_run_use_case,
    get_get_training_run_use_case,
    get_list_training_predictions_use_case,
    get_list_training_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.training_run import (
    CreateBaselineTrainingRunRequestBody,
    TrainingPredictionResponse,
    TrainingRunResponse,
)
from blueberry_microid.ml.configs.training_config import TrainingConfig

router = APIRouter(prefix="/ml/training-runs", tags=["training-runs"])


@router.post("/baseline", response_model=TrainingRunResponse, status_code=status.HTTP_201_CREATED)
def create_baseline_training_run(
    payload: CreateBaselineTrainingRunRequestBody,
    use_case: CreateBaselineTrainingRunUseCase = Depends(get_create_baseline_training_run_use_case),
) -> TrainingRunResponse:
    dto = use_case.execute(
        CreateBaselineTrainingRunRequest(
            dataset_release_id=payload.dataset_release_id,
            preflight_run_id=payload.preflight_run_id,
            experiment_name=payload.experiment_name,
            training_config=TrainingConfig.from_dict(payload.training_config.model_dump()),
            baseline_model_type=payload.baseline_model_type,
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return TrainingRunResponse.model_validate(dto)


@router.get("", response_model=list[TrainingRunResponse])
def list_training_runs(
    use_case: ListTrainingRunsUseCase = Depends(get_list_training_runs_use_case),
) -> list[TrainingRunResponse]:
    return [TrainingRunResponse.model_validate(dto) for dto in use_case.execute()]


@router.get("/{training_run_id}", response_model=TrainingRunResponse)
def get_training_run(
    training_run_id: UUID,
    use_case: GetTrainingRunUseCase = Depends(get_get_training_run_use_case),
) -> TrainingRunResponse:
    return TrainingRunResponse.model_validate(use_case.execute(training_run_id))


@router.get("/{training_run_id}/predictions", response_model=list[TrainingPredictionResponse])
def list_training_predictions(
    training_run_id: UUID,
    split: DatasetSplit | None = Query(default=None),
    use_case: ListTrainingPredictionsUseCase = Depends(get_list_training_predictions_use_case),
) -> list[TrainingPredictionResponse]:
    return [TrainingPredictionResponse.model_validate(dto) for dto in use_case.execute(training_run_id, split)]
