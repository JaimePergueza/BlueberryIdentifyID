from datetime import datetime, timezone
from uuid import uuid4

from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus
from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus
from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_config import DetectionTrainingConfig
from blueberry_microid.ml.training.yolo_dry_run_trainer import YoloDryRunTrainer
from tests.unit.application.test_annotation_bundle_services import _export_run, _item
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle

_FORBIDDEN_WORDS = ("bacteria", "fungi", "colony", "species", "genus", "taxon", "diagnosis")


def _quality_gate(bundle, *, status=AnnotationQualityGateStatus.PASSED, error_count=0, warning_count=0):
    return AnnotationQualityGateRun(
        annotation_bundle_run_id=bundle.id,
        dataset_release_id=bundle.dataset_release_id,
        petri_annotation_export_run_id=bundle.petri_annotation_export_run_id,
        status=status,
        is_passed=status == AnnotationQualityGateStatus.PASSED,
        config={},
        total_images=1,
        total_annotations=1,
        train_image_count=1,
        validation_image_count=0,
        test_image_count=0,
        train_annotation_count=1,
        validation_annotation_count=0,
        test_annotation_count=0,
        error_count=error_count,
        warning_count=warning_count,
        quality_summary={},
        split_distribution={},
        bbox_statistics={},
        category_distribution={},
    )


def test_generates_planned_plan_when_bundle_completed_and_gate_passed(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert plan.status == DetectionTrainingStatus.PLANNED
    assert plan.is_runnable is True


def test_generates_command_preview_without_executing(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert plan.command_preview["dry_run_only"] is True
    assert plan.command_preview["tool"] == "ultralytics_yolo"
    assert "yolo detect train" in plan.command_preview["command"]


def test_generates_expected_outputs(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert "weights_path_planned" in plan.expected_outputs
    assert "metrics_path_planned" in plan.expected_outputs
    assert "predictions_path_planned" in plan.expected_outputs
    assert "run_dir_planned" in plan.expected_outputs


def test_adds_info_issue_no_training_executed(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert any(issue.code == "no_training_executed" for issue in plan.issues)


def test_blocks_when_bundle_is_dry_run(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    bundle.status = AnnotationBundleStatus.DRY_RUN
    bundle.dry_run = True
    gate = _quality_gate(bundle)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert plan.status == DetectionTrainingStatus.BLOCKED
    assert plan.is_runnable is False
    assert any(issue.code == "bundle_not_completed" for issue in plan.issues)


def test_blocks_when_bundle_failed(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    bundle.status = AnnotationBundleStatus.FAILED
    bundle.is_completed = False
    gate = _quality_gate(bundle)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert plan.status == DetectionTrainingStatus.BLOCKED
    assert any(issue.code == "bundle_not_completed" for issue in plan.issues)


def test_blocks_when_quality_gate_missing(tmp_path):
    bundle, files = _completed_bundle(tmp_path)

    plan = YoloDryRunTrainer().plan_training(bundle, files, None, DetectionTrainingConfig())

    assert plan.status == DetectionTrainingStatus.BLOCKED
    assert any(issue.code == "quality_gate_missing" for issue in plan.issues)


def test_blocks_when_quality_gate_warning_and_required_passed(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle, status=AnnotationQualityGateStatus.WARNING, warning_count=1)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert plan.status == DetectionTrainingStatus.BLOCKED
    assert any(issue.code == "quality_gate_not_passed" for issue in plan.issues)


def test_blocks_when_quality_gate_failed(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle, status=AnnotationQualityGateStatus.FAILED, error_count=1)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert plan.status == DetectionTrainingStatus.BLOCKED
    assert any(issue.code == "quality_gate_not_passed" for issue in plan.issues)


def test_blocks_when_dataset_yaml_missing(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)
    files_without_yaml = [f for f in files if f.file_role.value != "dataset_yaml"]

    plan = YoloDryRunTrainer().plan_training(bundle, files_without_yaml, gate, DetectionTrainingConfig())

    assert plan.status == DetectionTrainingStatus.BLOCKED
    assert any(issue.code == "dataset_yaml_missing" for issue in plan.issues)


def test_blocks_when_yolo_labels_missing(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)
    files_without_labels = [f for f in files if f.file_role.value != "yolo_label"]

    plan = YoloDryRunTrainer().plan_training(bundle, files_without_labels, gate, DetectionTrainingConfig())

    assert plan.status == DetectionTrainingStatus.BLOCKED
    assert any(issue.code == "yolo_labels_missing" for issue in plan.issues)


def test_rejects_unsupported_algorithm(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)
    config = DetectionTrainingConfig()
    object.__setattr__(config, "algorithm", "yolo_train_fake")

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, config)

    assert any(issue.code == "unsupported_algorithm" for issue in plan.issues)


def test_rejects_unsupported_mode(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)
    config = DetectionTrainingConfig()
    object.__setattr__(config, "mode", "real_run_fake")

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, config)

    assert any(issue.code == "unsupported_mode" for issue in plan.issues)


def test_warns_when_external_weights_allowed(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)
    config = DetectionTrainingConfig(allow_external_weights=True, pretrained_weights_path="s3://bucket/weights.pt")

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, config)

    assert any(issue.code == "external_weights_requested" for issue in plan.issues)


def test_does_not_import_ultralytics():
    import sys

    assert "ultralytics" not in sys.modules


def test_does_not_import_torch():
    import sys

    assert "torch" not in sys.modules


def test_does_not_write_files(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)
    before = set(tmp_path.rglob("*"))

    YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    after = set(tmp_path.rglob("*"))
    assert before == after


def test_does_not_create_weights_file(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)

    YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    assert not list(tmp_path.rglob("*.pt"))
    assert not list(tmp_path.rglob("*.onnx"))
    assert not list(tmp_path.rglob("*.h5"))


def test_does_not_use_taxonomy(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    gate = _quality_gate(bundle)

    plan = YoloDryRunTrainer().plan_training(bundle, files, gate, DetectionTrainingConfig())

    haystack = str(plan.training_plan).lower() + str(plan.command_preview).lower() + str(plan.dataset_summary).lower()
    for word in _FORBIDDEN_WORDS:
        assert word not in haystack
