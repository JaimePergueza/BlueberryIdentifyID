from pathlib import Path
from uuid import uuid4

import pytest

from blueberry_microid.application.services.promotion_gate_evaluator import PromotionGateEvaluator
from blueberry_microid.application.services.results_csv_parser import ResultsCsvParser, ResultsCsvParserError
from blueberry_microid.application.services.smoke_model_evaluator import SmokeModelEvaluator
from blueberry_microid.domain.entities.model_candidate import ModelCandidate
from blueberry_microid.domain.enums.model_candidate_kind import ModelCandidateKind
from blueberry_microid.domain.enums.model_candidate_status import ModelCandidateStatus


def _candidate(results_path: Path) -> ModelCandidate:
    return ModelCandidate(
        local_yolo_training_execution_run_id=uuid4(),
        detection_training_run_id=uuid4(),
        candidate_kind=ModelCandidateKind.SMOKE_YOLO,
        status=ModelCandidateStatus.CREATED,
        model_artifact_path=str(results_path.parent / "weights" / "best.pt"),
        model_artifact_checksum_sha256="a" * 64,
        model_artifact_size_bytes=10,
        metrics_artifact_path=str(results_path),
        config_artifact_path=str(results_path.parent / "args.yaml"),
    )


def test_results_csv_parser_reads_zero_smoke_metrics(tmp_path):
    results = tmp_path / "results.csv"
    results.write_text(
        "epoch,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),train/box_loss\n"
        "1,0,0,0,0,5.5\n",
        encoding="utf-8",
    )

    parsed = ResultsCsvParser().parse(results)

    assert parsed["latest"]["precision"] == 0
    assert parsed["latest"]["core_metrics_all_zero"] is True
    assert any(issue["code"] == "core_metrics_zero" for issue in parsed["issues"])


def test_results_csv_parser_fails_for_missing_file(tmp_path):
    with pytest.raises(ResultsCsvParserError):
        ResultsCsvParser().parse(tmp_path / "missing.csv")


def test_smoke_model_evaluator_blocks_minimal_zero_metric_candidate(tmp_path):
    results = tmp_path / "results.csv"
    results.write_text(
        "epoch,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B)\n"
        "1,0,0,0,0\n",
        encoding="utf-8",
    )

    run, issues = SmokeModelEvaluator().evaluate(_candidate(results))
    gate = PromotionGateEvaluator().evaluate(_candidate(results), run)

    assert run.decision.value == "smoke_only"
    assert gate.decision.value == "not_promotable"
    assert {issue.code for issue in issues} >= {"smoke_only", "metrics_zero", "dataset_insufficient"}


def test_model_evaluation_services_do_not_import_training_frameworks():
    source_files = [
        Path("src/blueberry_microid/application/services/results_csv_parser.py"),
        Path("src/blueberry_microid/application/services/smoke_model_evaluator.py"),
        Path("src/blueberry_microid/application/services/promotion_gate_evaluator.py"),
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_files)
    assert "ultralytics" not in source
    assert "torch" not in source
