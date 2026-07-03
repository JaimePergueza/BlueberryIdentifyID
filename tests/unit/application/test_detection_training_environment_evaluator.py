import sys

from blueberry_microid.application.services.detection_training_environment_evaluator import (
    DetectionTrainingEnvironmentEvaluator,
)
from blueberry_microid.domain.entities.detection_training_readiness_report import DetectionTrainingReadinessReport
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_environment_decision import (
    DetectionTrainingEnvironmentDecision,
)
from blueberry_microid.domain.enums.detection_training_environment_status import DetectionTrainingEnvironmentStatus
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_environment_config import DetectionTrainingEnvironmentConfig
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle

_FORBIDDEN_WORDS = ("bacteria", "fungi", "colony", "species", "genus", "taxon", "diagnosis")


def _planned_run(bundle):
    return DetectionTrainingRun(
        annotation_bundle_run_id=bundle.id,
        dataset_release_id=bundle.dataset_release_id,
        petri_annotation_export_run_id=bundle.petri_annotation_export_run_id,
        annotation_quality_gate_run_id=None,
        algorithm=DetectionTrainingAlgorithm.YOLO_DRY_RUN,
        mode=DetectionTrainingMode.DRY_RUN,
        status=DetectionTrainingStatus.PLANNED,
        is_runnable=True,
        config={},
        training_plan={"planned": True},
        command_preview={"dry_run_only": True, "command": "yolo detect train ..."},
        dataset_summary={},
        quality_gate_summary={},
        expected_outputs={"weights_path_planned": "planned/weights.pt"},
        issue_count=0,
        warning_count=0,
        error_count=0,
    )


def _readiness_report(
    run,
    bundle,
    *,
    status=DetectionTrainingReadinessStatus.READY,
    decision=DetectionTrainingReadinessDecision.READY_FOR_TRAINING,
    error_count=0,
    is_ready=True,
):
    return DetectionTrainingReadinessReport(
        detection_training_run_id=run.id,
        annotation_bundle_run_id=bundle.id,
        dataset_release_id=bundle.dataset_release_id,
        petri_annotation_export_run_id=bundle.petri_annotation_export_run_id,
        decision=decision,
        status=status,
        is_ready=is_ready,
        config={},
        data_summary={},
        split_summary={},
        quality_summary={},
        environment_summary={},
        contract_summary={},
        risk_summary={},
        recommendation_summary={},
        error_count=error_count,
        warning_count=0,
        info_count=0,
    )


def _setup(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    run = _planned_run(bundle)
    readiness = _readiness_report(run, bundle)
    return run, bundle, files, readiness


def _evaluate(run, files, bundle, readiness, config=None, readiness_issues=None):
    return DetectionTrainingEnvironmentEvaluator().evaluate(
        run,
        readiness,
        readiness_issues or [],
        bundle,
        files,
        config or DetectionTrainingEnvironmentConfig(),
    )


def test_environment_ready_when_readiness_ready_and_config_minimal(tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(
        allow_cpu_training=False,
        artifact_output_dir=str(tmp_path),
        pretrained_weights_policy="not_applicable",
    )

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert evaluation.decision == DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY
    assert evaluation.is_environment_ready is True


def test_blocked_if_readiness_status_blocked(tmp_path):
    run, bundle, files, _ = _setup(tmp_path)
    readiness = _readiness_report(
        run, bundle, status=DetectionTrainingReadinessStatus.BLOCKED, error_count=1, is_ready=False
    )

    evaluation = _evaluate(run, files, bundle, readiness)

    assert evaluation.status == DetectionTrainingEnvironmentStatus.BLOCKED
    assert any(issue.code == "readiness_not_ready" for issue in evaluation.errors)
    assert evaluation.is_environment_ready is False


def test_blocked_if_readiness_status_failed(tmp_path):
    run, bundle, files, _ = _setup(tmp_path)
    readiness = _readiness_report(
        run,
        bundle,
        status=DetectionTrainingReadinessStatus.FAILED,
        decision=DetectionTrainingReadinessDecision.BLOCKED_BY_CONTRACT,
        is_ready=False,
    )

    evaluation = _evaluate(run, files, bundle, readiness)

    assert any(issue.code == "readiness_not_ready" for issue in evaluation.errors)


def test_blocked_if_readiness_decision_not_ready_for_training(tmp_path):
    run, bundle, files, _ = _setup(tmp_path)
    readiness = _readiness_report(
        run,
        bundle,
        status=DetectionTrainingReadinessStatus.WARNING,
        decision=DetectionTrainingReadinessDecision.NEEDS_MORE_ANNOTATIONS,
        is_ready=False,
    )

    evaluation = _evaluate(run, files, bundle, readiness)

    assert any(issue.code == "readiness_not_ready" for issue in evaluation.errors)
    assert evaluation.is_environment_ready is False


def test_detects_python_version(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, readiness)

    version_info = sys.version_info
    expected = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    assert evaluation.detected_environment["detected_python_version"] == expected


def test_detects_platform(tmp_path):
    import platform

    run, bundle, files, readiness = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, readiness)

    assert evaluation.detected_environment["detected_os"] == platform.system()


def test_blocks_on_incompatible_target_python_version(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(target_python_version="1.0")

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "python_version_mismatch" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingEnvironmentDecision.BLOCKED_BY_UNSUPPORTED_PLATFORM


def test_blocks_on_incompatible_target_os(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(target_os="NotARealOS")

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "unsupported_os" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingEnvironmentDecision.BLOCKED_BY_UNSUPPORTED_PLATFORM


def test_does_not_import_torch(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)

    _evaluate(run, files, bundle, readiness)

    assert "torch" not in sys.modules


def test_does_not_import_ultralytics(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)

    _evaluate(run, files, bundle, readiness)

    assert "ultralytics" not in sys.modules


def test_blocks_if_require_ultralytics_and_not_available(tmp_path, monkeypatch):
    import blueberry_microid.application.services.detection_training_environment_evaluator as evaluator_module

    monkeypatch.setattr(evaluator_module.importlib.util, "find_spec", lambda name: None)
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(require_ultralytics=True)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "ultralytics_not_installed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS
    assert "ultralytics" not in sys.modules


def test_blocks_if_require_torch_and_not_available(tmp_path, monkeypatch):
    import blueberry_microid.application.services.detection_training_environment_evaluator as evaluator_module

    monkeypatch.setattr(evaluator_module.importlib.util, "find_spec", lambda name: None)
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(require_torch=True)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "torch_not_installed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS
    assert "torch" not in sys.modules


def test_warning_info_if_dependency_installation_not_allowed(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(allow_dependency_installation=False)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "dependency_installation_not_allowed" for issue in evaluation.infos)


def test_warning_if_allow_cpu_training(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(allow_cpu_training=True)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "manual_training_required" for issue in evaluation.warnings)


def test_blocks_if_require_gpu(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(require_gpu=True)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "gpu_not_available" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS


def test_blocks_if_require_cuda(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(require_cuda=True)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "cuda_not_available" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS


def test_error_if_pretrained_weights_path_and_external_weights_disallowed(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(
        pretrained_weights_path="s3://bucket/weights.pt", allow_external_weights=False
    )

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "external_weights_not_allowed" for issue in evaluation.errors)


def test_info_if_external_weights_allowed(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(allow_external_weights=True)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "external_weights_policy_declared" for issue in evaluation.infos)


def test_warning_if_artifact_output_dir_missing(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(artifact_output_dir=None)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "output_dir_not_specified" for issue in evaluation.warnings)


def test_error_if_output_dir_inside_repo_and_not_allowed(tmp_path):
    import blueberry_microid.application.services.detection_training_environment_evaluator as evaluator_module

    repo_root = __import__("pathlib").Path(evaluator_module.__file__).resolve().parents[4]
    inside_dir = repo_root / "some_artifact_dir_for_test"

    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(
        artifact_output_dir=str(inside_dir), allow_artifacts_inside_repo=False
    )

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "artifact_storage_policy_missing" for issue in evaluation.errors)


def test_issue_ci_training_not_allowed_when_allow_ci_training_true(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(allow_ci_training=True)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert any(issue.code == "ci_training_not_allowed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingEnvironmentDecision.BLOCKED_BY_POLICY


def test_issue_no_training_executed_always_present(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, readiness)

    assert any(issue.code == "no_training_executed" for issue in evaluation.infos)


def test_issue_environment_check_safe_only_always_present(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, readiness)

    assert any(issue.code == "environment_check_safe_only" for issue in evaluation.infos)


def test_blocks_if_taxonomic_category_detected(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    bundle.config = dict(bundle.config)
    bundle.config["categories"] = ["bacteria_colony"]

    evaluation = _evaluate(run, files, bundle, readiness)

    assert any(issue.code == "taxonomy_not_allowed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingEnvironmentDecision.BLOCKED_BY_POLICY


def test_generates_dependency_policy(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(require_ultralytics=True, target_ultralytics_version="8.0.0")

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert evaluation.dependency_policy["require_ultralytics"] is True
    assert evaluation.dependency_policy["target_ultralytics_version"] == "8.0.0"
    assert "ultralytics_available" in evaluation.dependency_policy


def test_generates_hardware_policy(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(require_gpu=True)

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert evaluation.hardware_policy["require_gpu"] is True
    assert evaluation.hardware_policy["gpu_available_verified"] is False


def test_generates_artifact_policy(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, readiness)

    assert "write_check_performed" in evaluation.artifact_policy
    assert evaluation.artifact_policy["write_check_performed"] is False


def test_generates_execution_policy(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)

    evaluation = _evaluate(run, files, bundle, readiness)

    assert evaluation.execution_policy["allow_ci_training"] is False
    assert "detected_ci" in evaluation.execution_policy


def test_generates_setup_instructions(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(require_ultralytics=True, target_ultralytics_version="8.0.0")

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    assert evaluation.setup_instructions["commands_executed"] is False
    assert any("ultralytics" in cmd for cmd in evaluation.setup_instructions["suggested_commands"])


def test_does_not_execute_commands(tmp_path, monkeypatch):
    import subprocess

    def _fail(*args, **kwargs):
        raise AssertionError("subprocess must never be invoked by the environment evaluator")

    monkeypatch.setattr(subprocess, "run", _fail)
    monkeypatch.setattr(subprocess, "Popen", _fail)

    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(
        require_ultralytics=True, require_torch=True, require_gpu=True, require_cuda=True
    )

    _evaluate(run, files, bundle, readiness, config=config)


def test_does_not_write_files(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    before = set(tmp_path.rglob("*"))

    _evaluate(run, files, bundle, readiness)

    after = set(tmp_path.rglob("*"))
    assert before == after


def test_does_not_download_anything(tmp_path):
    run, bundle, files, readiness = _setup(tmp_path)
    config = DetectionTrainingEnvironmentConfig(
        allow_external_weights=True, pretrained_weights_path="https://example.com/weights.pt"
    )

    evaluation = _evaluate(run, files, bundle, readiness, config=config)

    haystack = str(evaluation.artifact_policy).lower()
    assert "downloaded" not in haystack or "not downloaded" in haystack or "nothing" in haystack
