from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Request

from blueberry_microid.application.dto.model_evaluation_dto import (
    CreateModelCandidateFromLocalTrainingRunRequest,
)
from blueberry_microid.application.use_cases.model_evaluation import (
    CreateModelCandidateFromLocalTrainingRunUseCase,
    EvaluateModelCandidateUseCase,
    GetModelCandidateUseCase,
    GetModelEvaluationRunUseCase,
    GetModelPromotionGateRunUseCase,
    ListModelCandidatesUseCase,
    ListModelEvaluationIssuesUseCase,
    ListModelEvaluationRunsUseCase,
    ListModelPromotionGateRunsUseCase,
    RunModelPromotionGateUseCase,
)
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from blueberry_microid.interfaces.api.v1.schemas.model_evaluation import (
    CreateModelCandidateFromLocalYoloRunRequestBody,
    ModelCandidateListResponse,
    ModelCandidateResponse,
    ModelEvaluationIssueListResponse,
    ModelEvaluationIssueResponse,
    ModelEvaluationRunListResponse,
    ModelEvaluationRunResponse,
    ModelPromotionGateRunListResponse,
    ModelPromotionGateRunResponse,
    RunPromotionGateRequestBody,
)

router = APIRouter(tags=["model-evaluation"])


def _uow(request: Request) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(request.app.state.session_factory)


@router.post("/ml/model-candidates/from-local-yolo-run", response_model=ModelCandidateResponse, status_code=201)
def create_model_candidate_from_local_yolo_run(
    payload: CreateModelCandidateFromLocalYoloRunRequestBody,
    request: Request,
) -> ModelCandidateResponse:
    use_case = CreateModelCandidateFromLocalTrainingRunUseCase(_uow(request), repo_root=Path.cwd())
    dto = use_case.execute(
        CreateModelCandidateFromLocalTrainingRunRequest(
            local_yolo_training_execution_run_id=payload.local_yolo_training_execution_run_id,
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return ModelCandidateResponse.model_validate(dto)


@router.get("/ml/model-candidates", response_model=ModelCandidateListResponse)
def list_model_candidates(request: Request) -> ModelCandidateListResponse:
    return ModelCandidateListResponse(
        model_candidates=[ModelCandidateResponse.model_validate(dto) for dto in ListModelCandidatesUseCase(_uow(request)).execute()]
    )


@router.get("/ml/model-candidates/{model_candidate_id}", response_model=ModelCandidateResponse)
def get_model_candidate(model_candidate_id: UUID, request: Request) -> ModelCandidateResponse:
    return ModelCandidateResponse.model_validate(GetModelCandidateUseCase(_uow(request)).execute(model_candidate_id))


@router.post("/ml/model-candidates/{model_candidate_id}/evaluations", response_model=ModelEvaluationRunResponse, status_code=201)
def evaluate_model_candidate(model_candidate_id: UUID, request: Request) -> ModelEvaluationRunResponse:
    return ModelEvaluationRunResponse.model_validate(EvaluateModelCandidateUseCase(_uow(request)).execute(model_candidate_id))


@router.get("/ml/model-candidates/{model_candidate_id}/evaluations", response_model=ModelEvaluationRunListResponse)
def list_model_evaluations(model_candidate_id: UUID, request: Request) -> ModelEvaluationRunListResponse:
    return ModelEvaluationRunListResponse(
        model_evaluations=[
            ModelEvaluationRunResponse.model_validate(dto)
            for dto in ListModelEvaluationRunsUseCase(_uow(request)).execute(model_candidate_id)
        ]
    )


@router.get("/ml/model-evaluations/{model_evaluation_run_id}", response_model=ModelEvaluationRunResponse)
def get_model_evaluation(model_evaluation_run_id: UUID, request: Request) -> ModelEvaluationRunResponse:
    return ModelEvaluationRunResponse.model_validate(
        GetModelEvaluationRunUseCase(_uow(request)).execute(model_evaluation_run_id)
    )


@router.get("/ml/model-evaluations/{model_evaluation_run_id}/issues", response_model=ModelEvaluationIssueListResponse)
def list_model_evaluation_issues(model_evaluation_run_id: UUID, request: Request) -> ModelEvaluationIssueListResponse:
    return ModelEvaluationIssueListResponse(
        issues=[
            ModelEvaluationIssueResponse.model_validate(dto)
            for dto in ListModelEvaluationIssuesUseCase(_uow(request)).execute(model_evaluation_run_id)
        ]
    )


@router.post("/ml/model-evaluations/{model_evaluation_run_id}/promotion-gate", response_model=ModelPromotionGateRunResponse, status_code=201)
def run_model_promotion_gate(
    model_evaluation_run_id: UUID,
    payload: RunPromotionGateRequestBody,
    request: Request,
) -> ModelPromotionGateRunResponse:
    return ModelPromotionGateRunResponse.model_validate(
        RunModelPromotionGateUseCase(_uow(request)).execute(
            model_evaluation_run_id, created_by=payload.created_by, notes=payload.notes
        )
    )


@router.get("/ml/model-promotion-gates/{promotion_gate_run_id}", response_model=ModelPromotionGateRunResponse)
def get_model_promotion_gate(promotion_gate_run_id: UUID, request: Request) -> ModelPromotionGateRunResponse:
    return ModelPromotionGateRunResponse.model_validate(
        GetModelPromotionGateRunUseCase(_uow(request)).execute(promotion_gate_run_id)
    )


@router.get("/ml/model-candidates/{model_candidate_id}/promotion-gates", response_model=ModelPromotionGateRunListResponse)
def list_model_promotion_gates(model_candidate_id: UUID, request: Request) -> ModelPromotionGateRunListResponse:
    return ModelPromotionGateRunListResponse(
        promotion_gates=[
            ModelPromotionGateRunResponse.model_validate(dto)
            for dto in ListModelPromotionGateRunsUseCase(_uow(request)).execute(model_candidate_id)
        ]
    )
