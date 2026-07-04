from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import UUID

from blueberry_microid.application.dto.model_evaluation_dto import (
    CreateModelCandidateFromLocalTrainingRunRequest,
    ModelCandidateDTO,
    ModelEvaluationIssueDTO,
    ModelEvaluationRunDTO,
    ModelPromotionGateRunDTO,
)
from blueberry_microid.application.exceptions import NotFoundError
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.model_candidate_builder import ModelCandidateBuilder
from blueberry_microid.application.services.promotion_gate_evaluator import PromotionGateEvaluator
from blueberry_microid.application.services.smoke_model_evaluator import SmokeModelEvaluator


class CreateModelCandidateFromLocalTrainingRunUseCase:
    def __init__(self, uow: UnitOfWorkPort, *, repo_root: Path) -> None:
        self._uow = uow
        self._repo_root = repo_root

    def execute(self, request: CreateModelCandidateFromLocalTrainingRunRequest) -> ModelCandidateDTO:
        with self._uow as uow:
            builder = ModelCandidateBuilder(
                uow.detection_training_execution_run_repository,
                uow.detection_training_artifact_record_repository,
                repo_root=self._repo_root,
            )
            candidate = builder.build(
                request.local_yolo_training_execution_run_id,
                created_by=request.created_by,
                notes=request.notes,
            )
            saved = uow.model_candidate_repository.add(candidate)
            uow.commit()
        return ModelCandidateDTO.from_entity(saved)


class EvaluateModelCandidateUseCase:
    def __init__(self, uow: UnitOfWorkPort, evaluator: SmokeModelEvaluator | None = None) -> None:
        self._uow = uow
        self._evaluator = evaluator or SmokeModelEvaluator()

    def execute(self, model_candidate_id: UUID) -> ModelEvaluationRunDTO:
        with self._uow as uow:
            candidate = uow.model_candidate_repository.get_by_id(model_candidate_id)
            if candidate is None:
                raise NotFoundError(f"model candidate not found: {model_candidate_id}")
            run, issues = self._evaluator.evaluate(candidate)
            saved_run = uow.model_evaluation_run_repository.add(run)
            fixed_issues = [replace(issue, model_evaluation_run_id=saved_run.id) for issue in issues]
            uow.model_evaluation_issue_repository.add_many(fixed_issues)
            uow.commit()
        return ModelEvaluationRunDTO.from_entity(saved_run)


class RunModelPromotionGateUseCase:
    def __init__(self, uow: UnitOfWorkPort, evaluator: PromotionGateEvaluator | None = None) -> None:
        self._uow = uow
        self._evaluator = evaluator or PromotionGateEvaluator()

    def execute(self, model_evaluation_run_id: UUID, *, created_by: str | None = None, notes: str | None = None) -> ModelPromotionGateRunDTO:
        with self._uow as uow:
            evaluation = uow.model_evaluation_run_repository.get_by_id(model_evaluation_run_id)
            if evaluation is None:
                raise NotFoundError(f"model evaluation run not found: {model_evaluation_run_id}")
            candidate = uow.model_candidate_repository.get_by_id(evaluation.model_candidate_id)
            if candidate is None:
                raise NotFoundError(f"model candidate not found: {evaluation.model_candidate_id}")
            gate = self._evaluator.evaluate(candidate, evaluation, created_by=created_by, notes=notes)
            saved = uow.model_promotion_gate_run_repository.add(gate)
            uow.commit()
        return ModelPromotionGateRunDTO.from_entity(saved)


class GetModelCandidateUseCase:
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def execute(self, candidate_id: UUID) -> ModelCandidateDTO:
        with self._uow as uow:
            candidate = uow.model_candidate_repository.get_by_id(candidate_id)
        if candidate is None:
            raise NotFoundError(f"model candidate not found: {candidate_id}")
        return ModelCandidateDTO.from_entity(candidate)


class ListModelCandidatesUseCase:
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def execute(self) -> list[ModelCandidateDTO]:
        with self._uow as uow:
            candidates = uow.model_candidate_repository.list_all()
        return [ModelCandidateDTO.from_entity(candidate) for candidate in candidates]


class GetModelEvaluationRunUseCase:
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def execute(self, run_id: UUID) -> ModelEvaluationRunDTO:
        with self._uow as uow:
            run = uow.model_evaluation_run_repository.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"model evaluation run not found: {run_id}")
        return ModelEvaluationRunDTO.from_entity(run)


class ListModelEvaluationRunsUseCase:
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def execute(self, candidate_id: UUID) -> list[ModelEvaluationRunDTO]:
        with self._uow as uow:
            if uow.model_candidate_repository.get_by_id(candidate_id) is None:
                raise NotFoundError(f"model candidate not found: {candidate_id}")
            runs = uow.model_evaluation_run_repository.list_by_model_candidate_id(candidate_id)
        return [ModelEvaluationRunDTO.from_entity(run) for run in runs]


class ListModelEvaluationIssuesUseCase:
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def execute(self, run_id: UUID) -> list[ModelEvaluationIssueDTO]:
        with self._uow as uow:
            if uow.model_evaluation_run_repository.get_by_id(run_id) is None:
                raise NotFoundError(f"model evaluation run not found: {run_id}")
            issues = uow.model_evaluation_issue_repository.list_by_model_evaluation_run_id(run_id)
        return [ModelEvaluationIssueDTO.from_entity(issue) for issue in issues]


class GetModelPromotionGateRunUseCase:
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def execute(self, run_id: UUID) -> ModelPromotionGateRunDTO:
        with self._uow as uow:
            run = uow.model_promotion_gate_run_repository.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"model promotion gate run not found: {run_id}")
        return ModelPromotionGateRunDTO.from_entity(run)


class ListModelPromotionGateRunsUseCase:
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def execute(self, candidate_id: UUID) -> list[ModelPromotionGateRunDTO]:
        with self._uow as uow:
            if uow.model_candidate_repository.get_by_id(candidate_id) is None:
                raise NotFoundError(f"model candidate not found: {candidate_id}")
            runs = uow.model_promotion_gate_run_repository.list_by_model_candidate_id(candidate_id)
        return [ModelPromotionGateRunDTO.from_entity(run) for run in runs]
