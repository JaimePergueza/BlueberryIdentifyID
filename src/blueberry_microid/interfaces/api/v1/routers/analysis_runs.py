from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.analysis_run_dto import CreateAnalysisRunRequest
from blueberry_microid.application.use_cases.inference.create_analysis_run import CreateAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.get_analysis_run import GetAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.get_prediction import GetPredictionForAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.process_analysis_run import ProcessAnalysisRunUseCase
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.exceptions.errors import InvalidAnalysisRunTransitionError
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_analysis_run_use_case,
    get_get_analysis_run_use_case,
    get_get_prediction_use_case,
    get_process_analysis_run_task,
    get_process_analysis_run_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.analysis_run import (
    AnalysisRunAsyncProcessRead,
    AnalysisRunCreate,
    AnalysisRunProcessRead,
    AnalysisRunRead,
)
from blueberry_microid.interfaces.api.v1.schemas.prediction import PredictionRead

router = APIRouter(prefix="/analysis-runs", tags=["analysis-runs"])

_MOCK_DISCLAIMER = (
    "This result was produced by a simulated (mock) inference engine, for technical "
    "testing only. It does not perform real image analysis, has no diagnostic "
    "validity, and never identifies a microorganism species or genus."
)


@router.post("", response_model=AnalysisRunRead, status_code=status.HTTP_201_CREATED)
def create_analysis_run(
    payload: AnalysisRunCreate,
    use_case: CreateAnalysisRunUseCase = Depends(get_create_analysis_run_use_case),
) -> AnalysisRunRead:
    # CreateAnalysisRunUseCase resolves sample/petri_image/micro_image/
    # model_version and enforces that both images belong to `sample_id`
    # (see domain.exceptions.errors.CrossSampleAnalysisError). This handler
    # does not duplicate that check — it only shapes I/O. The resulting
    # AnalysisRun is always `pending`: no inference runs, no Prediction is
    # created, and nothing is queued to Celery.
    request = CreateAnalysisRunRequest(
        sample_id=payload.sample_id,
        petri_image_id=payload.petri_image_id,
        micro_image_id=payload.micro_image_id,
        model_version_id=payload.model_version_id,
    )
    dto = use_case.execute(request)
    return AnalysisRunRead.model_validate(dto)


@router.get("/{analysis_run_id}", response_model=AnalysisRunRead)
def get_analysis_run(
    analysis_run_id: UUID,
    use_case: GetAnalysisRunUseCase = Depends(get_get_analysis_run_use_case),
) -> AnalysisRunRead:
    dto = use_case.execute(analysis_run_id)
    return AnalysisRunRead.model_validate(dto)


@router.post("/{analysis_run_id}/process", response_model=AnalysisRunProcessRead, status_code=status.HTTP_200_OK)
def process_analysis_run(
    analysis_run_id: UUID,
    use_case: ProcessAnalysisRunUseCase = Depends(get_process_analysis_run_use_case),
) -> AnalysisRunProcessRead:
    # 200, not 201/202: this is a synchronous action on an *existing*
    # resource (like POST /orders/{id}/cancel), not a resource-creation
    # endpoint, and by the time this returns the work is already fully done
    # — there's nothing left "accepted for later" (no Celery yet), so 202
    # would be misleading. A Prediction is created as a side effect, but the
    # endpoint's primary subject is the AnalysisRun transition.
    #
    # If processing fails (including the mock engine raising), the use case
    # first marks the AnalysisRun `failed` with a controlled error_message,
    # then raises a controlled application error. The centralized error
    # handler turns that into a safe 500 response; this router only shapes
    # successful synchronous results.
    result = use_case.execute(analysis_run_id)
    return AnalysisRunProcessRead(
        analysis_run=AnalysisRunRead.model_validate(result.analysis_run),
        prediction=PredictionRead.model_validate(result.prediction) if result.prediction else None,
        disclaimer=_MOCK_DISCLAIMER,
    )


@router.post(
    "/{analysis_run_id}/process-async",
    response_model=AnalysisRunAsyncProcessRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def process_analysis_run_async(
    analysis_run_id: UUID,
    get_analysis_run_use_case: GetAnalysisRunUseCase = Depends(get_get_analysis_run_use_case),
    task=Depends(get_process_analysis_run_task),
) -> AnalysisRunAsyncProcessRead:
    # This endpoint is deliberately only a queueing boundary. It validates
    # the resource is currently pending, but it does not claim the row and
    # does not call the mock inference engine. The worker runs the same
    # ProcessAnalysisRunUseCase as the synchronous endpoint, so the atomic
    # claim remains the single source of truth for duplicate protection.
    analysis_run = get_analysis_run_use_case.execute(analysis_run_id)
    if analysis_run.status != AnalysisStatus.PENDING:
        raise InvalidAnalysisRunTransitionError(
            f"cannot queue AnalysisRun '{analysis_run_id}': it is not pending "
            f"(status='{analysis_run.status.value}')"
        )

    async_result = task.apply_async(args=[str(analysis_run_id)], queue="analysis")
    return AnalysisRunAsyncProcessRead(
        analysis_run_id=analysis_run_id,
        task_id=async_result.id,
        status="queued",
        message="Analysis processing has been queued",
    )


@router.get("/{analysis_run_id}/prediction", response_model=PredictionRead)
def get_prediction(
    analysis_run_id: UUID,
    use_case: GetPredictionForAnalysisRunUseCase = Depends(get_get_prediction_use_case),
) -> PredictionRead:
    dto = use_case.execute(analysis_run_id)
    return PredictionRead.model_validate(dto)
