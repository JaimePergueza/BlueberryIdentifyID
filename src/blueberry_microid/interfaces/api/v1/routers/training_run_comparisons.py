from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from blueberry_microid.application.dto.training_run_comparison_dto import CreateTrainingRunComparisonRequest
from blueberry_microid.application.use_cases.training.create_training_run_comparison import (
    CreateTrainingRunComparisonUseCase,
)
from blueberry_microid.application.use_cases.training.get_training_run_comparison import (
    GetTrainingRunComparisonUseCase,
)
from blueberry_microid.application.use_cases.training.list_training_run_comparison_entries import (
    ListTrainingRunComparisonEntriesUseCase,
)
from blueberry_microid.application.use_cases.training.list_training_run_comparisons import (
    ListTrainingRunComparisonsUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_training_run_comparison_use_case,
    get_get_training_run_comparison_use_case,
    get_list_training_run_comparison_entries_use_case,
    get_list_training_run_comparisons_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.training_run_comparison import (
    CreateTrainingRunComparisonRequestBody,
    TrainingRunComparisonEntryResponse,
    TrainingRunComparisonResponse,
)

router = APIRouter(tags=["training-run-comparisons"])


@router.post(
    "/ml/training-run-comparisons",
    response_model=TrainingRunComparisonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_training_run_comparison(
    payload: CreateTrainingRunComparisonRequestBody,
    use_case: CreateTrainingRunComparisonUseCase = Depends(get_create_training_run_comparison_use_case),
) -> TrainingRunComparisonResponse:
    dto = use_case.execute(
        CreateTrainingRunComparisonRequest(
            dataset_release_id=payload.dataset_release_id,
            training_run_ids=payload.training_run_ids,
            name=payload.name,
            description=payload.description,
            primary_metric=payload.primary_metric,
            primary_split=payload.primary_split,
            selection_policy=payload.selection_policy,
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return TrainingRunComparisonResponse.model_validate(dto)


@router.get("/ml/training-run-comparisons", response_model=list[TrainingRunComparisonResponse])
def list_training_run_comparisons(
    dataset_release_id: UUID | None = Query(default=None),
    use_case: ListTrainingRunComparisonsUseCase = Depends(get_list_training_run_comparisons_use_case),
) -> list[TrainingRunComparisonResponse]:
    return [TrainingRunComparisonResponse.model_validate(dto) for dto in use_case.execute(dataset_release_id)]


@router.get("/ml/training-run-comparisons/{comparison_id}", response_model=TrainingRunComparisonResponse)
def get_training_run_comparison(
    comparison_id: UUID,
    use_case: GetTrainingRunComparisonUseCase = Depends(get_get_training_run_comparison_use_case),
) -> TrainingRunComparisonResponse:
    return TrainingRunComparisonResponse.model_validate(use_case.execute(comparison_id))


@router.get(
    "/ml/training-run-comparisons/{comparison_id}/entries",
    response_model=list[TrainingRunComparisonEntryResponse],
)
def list_training_run_comparison_entries(
    comparison_id: UUID,
    use_case: ListTrainingRunComparisonEntriesUseCase = Depends(get_list_training_run_comparison_entries_use_case),
) -> list[TrainingRunComparisonEntryResponse]:
    return [TrainingRunComparisonEntryResponse.model_validate(dto) for dto in use_case.execute(comparison_id)]


@router.get(
    "/datasets/releases/{dataset_release_id}/training-run-comparisons",
    response_model=list[TrainingRunComparisonResponse],
)
def list_training_run_comparisons_for_dataset_release(
    dataset_release_id: UUID,
    use_case: ListTrainingRunComparisonsUseCase = Depends(get_list_training_run_comparisons_use_case),
) -> list[TrainingRunComparisonResponse]:
    return [TrainingRunComparisonResponse.model_validate(dto) for dto in use_case.execute(dataset_release_id)]
