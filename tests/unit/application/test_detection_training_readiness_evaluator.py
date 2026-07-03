from uuid import uuid4

from blueberry_microid.application.services.detection_training_readiness_evaluator import (
    DetectionTrainingReadinessEvaluator,
)
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus
from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus
from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_readiness_config import DetectionTrainingReadinessConfig
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle

_FORBIDDEN_WORDS = ("bacteria", "fungi", "colony", "species", "genus", "taxon", "diagnosis")


def _quality_gate(bundle, *, status=AnnotationQualityGateStatus.PASSED, error_count=0, warning_count=0, **overrides):
    fields = dict(
        annotation_bundle_run_id=bundle.id,
        dataset_release_id=bundle.dataset_release_id,
        petri_annotation_export_run_id=bundle.petri_annotation_export_run_id,
        status=status,
        is_passed=status == AnnotationQualityGateStatus.PASSED,
        config={},
        total_images=10,
        total_annotations=10,
        train_image_count=5,
        validation_image_count=2,
        test_image_count=2,
        train_annotation_count=5,
        validation_annotation_count=2,
        test_annotation_count=2,
        error_count=error_count,
        warning_count=warning_count,
        quality_summary={},
        split_distribution={},
        bbox_statistics={},
        category_distribution={"candidate_region": 10},
    )
    fields.update(overrides)
    return AnnotationQualityGateRun(**fields)


def _planned_run(bundle, gate, *, status=DetectionTrainingStatus.PLANNED, is_runnable=True, error_count=0):
    return DetectionTrainingRun(
        annotation_bundle_run_id=bundle.id,
        dataset_release_id=bundle.dataset_release_id,
        petri_annotation_export_run_id=bundle.petri_annotation_export_run_id,
        annotation_quality_gate_run_id=gate.id if gate is not None else None,
        algorithm=DetectionTrainingAlgorithm.YOLO_DRY_RUN,
        mode=DetectionTrainingMode.DRY_RUN,
        status=status,
        is_runnable=is_runnable,
        config={},
        training_plan={"planned": True},
        command_preview={"dry_run_only": True, "command": "yolo detect train ..."},
        dataset_summary={},
        quality_gate_summary={},
        expected_outputs={"weights_path_planned": "planned/weights.pt"},
        issue_count=0,
        warning_count=0,
        error_count=error_count,
    )


def _setup(tmp_path, *, gate_overrides=None, run_overrides=None):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle, **(gate_overrides or {}))
    run = _planned_run(bundle, gate, **(run_overrides or {}))
    return run, bundle, files, gate


def _evaluate(run, files, bundle, gate, config=None, run_issues=None, gate_issues=None):
    return DetectionTrainingReadinessEvaluator().evaluate(
        run,
        run_issues or [],
        bundle,
        files,
        gate,
        gate_issues or [],
        config or DetectionTrainingReadinessConfig(),
    )


def test_ready_for_training_when_all_minimums_met(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, gate)

    assert evaluation.decision == DetectionTrainingReadinessDecision.READY_FOR_TRAINING
    assert evaluation.is_ready is True


def test_blocks_if_run_not_planned(tmp_path):
    run, bundle, files, gate = _setup(
        tmp_path, run_overrides={"status": DetectionTrainingStatus.BLOCKED, "is_runnable": False, "error_count": 1}
    )

    evaluation = _evaluate(run, files, bundle, gate)

    assert evaluation.status == DetectionTrainingReadinessStatus.BLOCKED
    assert any(issue.code == "detection_training_not_planned" for issue in evaluation.errors)
    assert evaluation.is_ready is False


def test_blocks_if_is_runnable_false(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)
    run = _planned_run(bundle, gate, status=DetectionTrainingStatus.FAILED, is_runnable=False, error_count=1)

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "detection_training_not_planned" for issue in evaluation.errors)


def test_blocks_if_bundle_not_completed(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    bundle.status = AnnotationBundleStatus.FAILED

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "bundle_not_completed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingReadinessDecision.BLOCKED_BY_QUALITY


def test_blocks_if_quality_gate_not_passed(tmp_path):
    run, bundle, files, gate = _setup(
        tmp_path, gate_overrides={"status": AnnotationQualityGateStatus.FAILED, "error_count": 1}
    )

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "quality_gate_not_passed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingReadinessDecision.BLOCKED_BY_QUALITY


def test_blocks_if_dataset_yaml_missing(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    files_without_yaml = [f for f in files if f.file_role.value != "dataset_yaml"]

    evaluation = _evaluate(run, files_without_yaml, bundle, gate)

    assert any(issue.code == "dataset_yaml_missing" for issue in evaluation.errors)


def test_blocks_if_yolo_labels_missing(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    files_without_labels = [f for f in files if f.file_role.value != "yolo_label"]

    evaluation = _evaluate(run, files_without_labels, bundle, gate)

    assert any(issue.code == "yolo_labels_missing" for issue in evaluation.errors)


def test_needs_more_annotations_for_total_images(tmp_path):
    run, bundle, files, gate = _setup(tmp_path, gate_overrides={"total_images": 1})

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "insufficient_total_images" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingReadinessDecision.NEEDS_MORE_ANNOTATIONS


def test_needs_more_annotations_for_total_annotations(tmp_path):
    run, bundle, files, gate = _setup(tmp_path, gate_overrides={"total_annotations": 1})

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "insufficient_total_annotations" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingReadinessDecision.NEEDS_MORE_ANNOTATIONS


def test_needs_more_annotations_for_train_support(tmp_path):
    run, bundle, files, gate = _setup(tmp_path, gate_overrides={"train_image_count": 1, "train_annotation_count": 1})

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "insufficient_train_images" for issue in evaluation.errors)
    assert any(issue.code == "insufficient_train_annotations" for issue in evaluation.errors)


def test_needs_more_annotations_for_validation_support(tmp_path):
    run, bundle, files, gate = _setup(
        tmp_path, gate_overrides={"validation_image_count": 0, "validation_annotation_count": 0}
    )

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "insufficient_validation_images" for issue in evaluation.errors)
    assert any(issue.code == "insufficient_validation_annotations" for issue in evaluation.errors)


def test_needs_more_annotations_for_test_support(tmp_path):
    run, bundle, files, gate = _setup(tmp_path, gate_overrides={"test_image_count": 0, "test_annotation_count": 0})

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "insufficient_test_images" for issue in evaluation.errors)
    assert any(issue.code == "insufficient_test_annotations" for issue in evaluation.errors)


def test_warning_if_copy_images_false(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    assert bundle.config.get("copy_images") is False

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "copy_images_disabled" for issue in evaluation.warnings)


def test_info_no_training_executed(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "no_training_executed" for issue in evaluation.infos)


def test_warning_training_executor_missing_by_default(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "training_executor_missing" for issue in evaluation.warnings)
    assert evaluation.decision == DetectionTrainingReadinessDecision.READY_FOR_TRAINING


def test_blocked_when_require_ultralytics_installed(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    config = DetectionTrainingReadinessConfig(require_ultralytics_installed=True)

    evaluation = _evaluate(run, files, bundle, gate, config=config)

    assert any(issue.code == "ultralytics_not_installed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingReadinessDecision.BLOCKED_BY_ENVIRONMENT


def test_blocked_when_require_torch_installed(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    config = DetectionTrainingReadinessConfig(require_torch_installed=True)

    evaluation = _evaluate(run, files, bundle, gate, config=config)

    assert any(issue.code == "torch_not_installed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingReadinessDecision.BLOCKED_BY_ENVIRONMENT


def test_blocked_when_require_gpu(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    config = DetectionTrainingReadinessConfig(require_gpu=True)

    evaluation = _evaluate(run, files, bundle, gate, config=config)

    assert any(issue.code == "gpu_not_configured" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingReadinessDecision.BLOCKED_BY_ENVIRONMENT


def test_blocks_if_taxonomic_category_present(tmp_path):
    run, bundle, files, gate = _setup(
        tmp_path, gate_overrides={"category_distribution": {"candidate_region": 8, "bacteria_colony": 2}}
    )

    evaluation = _evaluate(run, files, bundle, gate)

    assert any(issue.code == "taxonomy_not_allowed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingReadinessDecision.BLOCKED_BY_CONFIGURATION


def test_calculates_data_summary(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, gate)

    assert evaluation.data_summary["total_images"] == 10
    assert evaluation.data_summary["total_annotations"] == 10
    assert evaluation.data_summary["determinable"] is True


def test_calculates_split_summary(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, gate)

    assert evaluation.split_summary["train"]["images"] == 5
    assert evaluation.split_summary["validation"]["images"] == 2
    assert evaluation.split_summary["test"]["images"] == 2


def test_calculates_quality_summary(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, gate)

    assert evaluation.quality_summary["bundle_status"] == "completed"
    assert evaluation.quality_summary["quality_gate_is_passed"] is True
    assert evaluation.quality_summary["dataset_yaml_present"] is True
    assert evaluation.quality_summary["yolo_labels_present"] is True


def test_calculates_environment_summary(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    config = DetectionTrainingReadinessConfig(require_gpu=True)

    evaluation = _evaluate(run, files, bundle, gate, config=config)

    assert evaluation.environment_summary["require_gpu"] is True
    assert evaluation.environment_summary["training_executor_available"] is False


def test_calculates_contract_summary(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, gate)

    assert evaluation.contract_summary["detection_training_run_status"] == "planned"
    assert evaluation.contract_summary["command_preview_executable"] is False
    assert evaluation.contract_summary["expected_outputs_are_real_files"] is False


def test_does_not_import_ultralytics(tmp_path):
    import sys

    run, bundle, files, gate = _setup(tmp_path)
    _evaluate(run, files, bundle, gate)

    assert "ultralytics" not in sys.modules


def test_does_not_import_torch(tmp_path):
    import sys

    run, bundle, files, gate = _setup(tmp_path)
    _evaluate(run, files, bundle, gate)

    assert "torch" not in sys.modules


def test_does_not_execute_commands(tmp_path, monkeypatch):
    import subprocess

    def _fail(*args, **kwargs):
        raise AssertionError("subprocess must never be invoked by the readiness evaluator")

    monkeypatch.setattr(subprocess, "run", _fail)
    monkeypatch.setattr(subprocess, "Popen", _fail)

    run, bundle, files, gate = _setup(tmp_path)
    _evaluate(run, files, bundle, gate)


def test_does_not_write_files(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)
    before = set(tmp_path.rglob("*"))

    _evaluate(run, files, bundle, gate)

    after = set(tmp_path.rglob("*"))
    assert before == after


def test_does_not_use_taxonomy_in_output(tmp_path):
    run, bundle, files, gate = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, gate)

    haystack = (
        str(evaluation.data_summary).lower()
        + str(evaluation.split_summary).lower()
        + str(evaluation.quality_summary).lower()
        + str(evaluation.environment_summary).lower()
        + str(evaluation.contract_summary).lower()
        + str(evaluation.risk_summary).lower()
        + str(evaluation.recommendation_summary).lower()
    )
    for word in _FORBIDDEN_WORDS:
        assert word not in haystack
