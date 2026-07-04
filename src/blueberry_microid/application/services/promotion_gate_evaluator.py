from __future__ import annotations

from blueberry_microid.domain.entities.model_candidate import ModelCandidate
from blueberry_microid.domain.entities.model_evaluation_run import ModelEvaluationRun
from blueberry_microid.domain.entities.model_promotion_gate_run import ModelPromotionGateRun
from blueberry_microid.domain.enums.model_promotion_decision import ModelPromotionDecision


class PromotionGateEvaluator:
    def evaluate(
        self,
        candidate: ModelCandidate,
        evaluation_run: ModelEvaluationRun,
        *,
        created_by: str | None = None,
        notes: str | None = None,
    ) -> ModelPromotionGateRun:
        reasons: list[dict] = []
        decision = ModelPromotionDecision.PROMOTABLE
        if evaluation_run.decision == ModelPromotionDecision.SMOKE_ONLY:
            decision = ModelPromotionDecision.NOT_PROMOTABLE
            reasons.append({"code": "smoke_only", "message": "Smoke model candidates cannot be promoted"})
        if evaluation_run.decision == ModelPromotionDecision.NOT_EVALUABLE:
            decision = ModelPromotionDecision.NOT_EVALUABLE
            reasons.append({"code": "not_evaluable", "message": "Evaluation did not produce usable metrics"})
        latest = evaluation_run.metrics_summary.get("latest", {})
        thresholds = evaluation_run.thresholds
        if latest.get("core_metrics_all_zero"):
            decision = ModelPromotionDecision.NOT_PROMOTABLE
            reasons.append({"code": "metrics_zero", "message": "Core metrics are zero"})
        if evaluation_run.dataset_summary.get("annotations", 0) < thresholds.get("min_annotations", 0):
            decision = ModelPromotionDecision.NOT_PROMOTABLE
            reasons.append({"code": "dataset_insufficient", "message": "Dataset is below required promotion thresholds"})
        if not candidate.model_artifact_checksum_sha256 or not candidate.model_artifact_path:
            decision = ModelPromotionDecision.BLOCKED_BY_POLICY
            reasons.append({"code": "artifact_metadata_missing", "message": "Model artifact metadata is incomplete"})
        return ModelPromotionGateRun(
            model_candidate_id=candidate.id,
            model_evaluation_run_id=evaluation_run.id,
            decision=decision,
            gate_summary={
                "promoted_to_model_version": False,
                "inference_enabled": False,
                "scientific_claim": "none",
            },
            blocking_reasons=reasons,
            required_thresholds=thresholds,
            observed_metrics=latest,
            created_by=created_by,
            notes=notes,
        )
