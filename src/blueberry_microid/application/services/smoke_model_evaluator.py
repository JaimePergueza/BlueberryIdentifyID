from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from blueberry_microid.application.services.results_csv_parser import ResultsCsvParser, ResultsCsvParserError
from blueberry_microid.domain.entities.model_candidate import ModelCandidate
from blueberry_microid.domain.entities.model_evaluation_issue import ModelEvaluationIssue
from blueberry_microid.domain.entities.model_evaluation_run import ModelEvaluationRun
from blueberry_microid.domain.enums.model_evaluation_issue_severity import ModelEvaluationIssueSeverity
from blueberry_microid.domain.enums.model_evaluation_status import ModelEvaluationStatus
from blueberry_microid.domain.enums.model_promotion_decision import ModelPromotionDecision


DEFAULT_PROMOTION_THRESHOLDS = {
    "min_train_images": 20,
    "min_val_images": 10,
    "min_annotations": 50,
    "min_map50": 0.50,
    "min_precision": 0.50,
    "min_recall": 0.50,
    "require_non_zero_metrics": True,
    "allow_smoke_only": True,
}


class SmokeModelEvaluator:
    def __init__(self, *, parser: ResultsCsvParser | None = None, thresholds: dict | None = None) -> None:
        self._parser = parser or ResultsCsvParser()
        self._thresholds = thresholds or DEFAULT_PROMOTION_THRESHOLDS.copy()

    def evaluate(self, candidate: ModelCandidate) -> tuple[ModelEvaluationRun, list[ModelEvaluationIssue]]:
        started_at = datetime.now(timezone.utc)
        issues: list[ModelEvaluationIssue] = []
        metrics_summary: dict = {}
        decision = ModelPromotionDecision.SMOKE_ONLY
        status = ModelEvaluationStatus.COMPLETED
        if candidate.metrics_artifact_path:
            try:
                metrics_summary = self._parser.parse(candidate.metrics_artifact_path)
            except ResultsCsvParserError as exc:
                decision = ModelPromotionDecision.NOT_EVALUABLE
                issues.append(self._issue(candidate.id, ModelEvaluationIssueSeverity.ERROR, "metrics_not_readable", str(exc)))
        else:
            decision = ModelPromotionDecision.NOT_EVALUABLE
            issues.append(self._issue(candidate.id, ModelEvaluationIssueSeverity.ERROR, "metrics_missing", "results.csv artifact is missing"))
        latest = metrics_summary.get("latest", {})
        if latest.get("core_metrics_all_zero"):
            issues.append(self._issue(candidate.id, ModelEvaluationIssueSeverity.WARNING, "metrics_zero", "Core YOLO metrics are zero; smoke model is not promotable"))
        for parser_issue in metrics_summary.get("issues", []):
            issues.append(self._issue(candidate.id, ModelEvaluationIssueSeverity.WARNING, parser_issue.get("code", "metrics_issue"), "results.csv parser reported an issue", parser_issue))
        dataset_summary = {"train_images": 1, "val_images": 1, "annotations": 3, "source": "fase37_smoke_yolo_view"}
        if dataset_summary["train_images"] < self._thresholds["min_train_images"] or dataset_summary["annotations"] < self._thresholds["min_annotations"]:
            issues.append(self._issue(candidate.id, ModelEvaluationIssueSeverity.WARNING, "dataset_insufficient", "Smoke dataset is below promotion thresholds", dataset_summary))
        issues.append(self._issue(candidate.id, ModelEvaluationIssueSeverity.INFO, "smoke_only", "This model candidate is a technical smoke artifact, not a scientific model"))
        if decision != ModelPromotionDecision.NOT_EVALUABLE:
            decision = ModelPromotionDecision.SMOKE_ONLY
        counts = self._counts(issues)
        run = ModelEvaluationRun(
            model_candidate_id=candidate.id,
            local_yolo_training_execution_run_id=candidate.local_yolo_training_execution_run_id,
            status=status,
            decision=decision,
            metrics_summary=metrics_summary,
            thresholds=self._thresholds,
            dataset_summary=dataset_summary,
            artifact_summary={
                "model_artifact_path": candidate.model_artifact_path,
                "model_artifact_checksum_sha256": candidate.model_artifact_checksum_sha256,
                "model_artifact_size_bytes": candidate.model_artifact_size_bytes,
                "metrics_artifact_path": candidate.metrics_artifact_path,
                "config_artifact_path": candidate.config_artifact_path,
                "weights_outside_repo": True,
                "metadata_only": True,
            },
            evaluation_summary={
                "scientific_claim": "none",
                "inference_performed": False,
                "training_performed": False,
                "weights_loaded": False,
                "candidate_kind": candidate.candidate_kind.value,
            },
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            warning_count=counts["warning"],
            error_count=counts["error"],
            info_count=counts["info"],
        )
        return run, issues

    def _issue(self, run_id_placeholder, severity, code: str, message: str, details: dict | None = None) -> ModelEvaluationIssue:
        return ModelEvaluationIssue(model_evaluation_run_id=run_id_placeholder, severity=severity, code=code, message=message, details=details)

    def _counts(self, issues: list[ModelEvaluationIssue]) -> dict[str, int]:
        return {
            "error": sum(1 for issue in issues if issue.severity == ModelEvaluationIssueSeverity.ERROR),
            "warning": sum(1 for issue in issues if issue.severity == ModelEvaluationIssueSeverity.WARNING),
            "info": sum(1 for issue in issues if issue.severity == ModelEvaluationIssueSeverity.INFO),
        }
