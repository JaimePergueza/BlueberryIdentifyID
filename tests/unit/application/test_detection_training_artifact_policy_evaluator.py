from pathlib import Path

from blueberry_microid.application.services.detection_training_artifact_policy_evaluator import (
    DetectionTrainingArtifactPolicyEvaluator,
)
from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_artifact_kind import DetectionTrainingArtifactKind
from blueberry_microid.domain.enums.detection_training_artifact_policy_decision import (
    DetectionTrainingArtifactPolicyDecision,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_status import (
    DetectionTrainingArtifactPolicyStatus,
)
from blueberry_microid.domain.enums.detection_training_environment_decision import (
    DetectionTrainingEnvironmentDecision,
)
from blueberry_microid.domain.enums.detection_training_environment_status import DetectionTrainingEnvironmentStatus
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_artifact_policy_config import (
    DetectionTrainingArtifactPolicyConfig,
)
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle

_FORBIDDEN_WORDS = ("bacteria", "fungi", "colony", "species", "genus", "taxon", "diagnosis")
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _planned_run(bundle, artifact_root: str = "/tmp/blueberry-artifacts"):
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
        expected_outputs={
            "weights_path_planned": f"{artifact_root}/run1/weights/best.pt",
            "metrics_path_planned": f"{artifact_root}/run1/results.csv",
            "predictions_path_planned": f"{artifact_root}/run1/predictions",
            "run_dir_planned": f"{artifact_root}/run1",
        },
        issue_count=0,
        warning_count=0,
        error_count=0,
    )


def _environment_spec(
    run,
    bundle,
    *,
    status=DetectionTrainingEnvironmentStatus.READY,
    decision=DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY,
    error_count=0,
    is_environment_ready=True,
):
    return DetectionTrainingEnvironmentSpec(
        detection_training_run_id=run.id,
        readiness_report_id=run.id,  # arbitrary placeholder UUID, unused by evaluator
        annotation_bundle_run_id=bundle.id,
        dataset_release_id=bundle.dataset_release_id,
        decision=decision,
        status=status,
        is_environment_ready=is_environment_ready,
        config={},
        detected_environment={},
        dependency_policy={},
        hardware_policy={},
        artifact_policy={},
        execution_policy={},
        setup_instructions={},
        safe_check_summary={},
        risk_summary={},
        recommendation_summary={},
        error_count=error_count,
        warning_count=0,
        info_count=0,
    )


def _setup(tmp_path, artifact_root=None):
    bundle, files = _completed_bundle(tmp_path)
    root = artifact_root or str(tmp_path / "artifacts")
    run = _planned_run(bundle, artifact_root=root)
    env_spec = _environment_spec(run, bundle)
    return run, bundle, files, env_spec


def _evaluate(run, bundle, files, env_spec, config=None):
    return DetectionTrainingArtifactPolicyEvaluator().evaluate(
        run, env_spec, bundle, files, config or DetectionTrainingArtifactPolicyConfig()
    )


def test_policy_ready_when_environment_ready_and_root_outside_repo(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(
        artifact_root_dir=str(tmp_path / "artifacts"), require_gitignore_rules=False
    )

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert evaluation.decision == DetectionTrainingArtifactPolicyDecision.ARTIFACT_POLICY_READY
    assert evaluation.is_policy_ready is True


def test_warning_when_environment_needs_manual_setup(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    env_spec = _environment_spec(
        run, bundle, status=DetectionTrainingEnvironmentStatus.WARNING,
        decision=DetectionTrainingEnvironmentDecision.NEEDS_MANUAL_SETUP,
        is_environment_ready=False,
    )
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert evaluation.status != DetectionTrainingArtifactPolicyStatus.BLOCKED
    assert not any(issue.code == "environment_not_ready" for issue in evaluation.errors)


def test_blocked_when_environment_blocked(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    env_spec = _environment_spec(
        run,
        bundle,
        status=DetectionTrainingEnvironmentStatus.BLOCKED,
        decision=DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS,
        error_count=1,
        is_environment_ready=False,
    )
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "environment_not_ready" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_ENVIRONMENT
    assert evaluation.is_policy_ready is False


def test_detects_weights_path_planned(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert evaluation.planned_output_summary["weights_path_planned"] == run.expected_outputs["weights_path_planned"]


def test_detects_metrics_path_planned(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert evaluation.planned_output_summary["metrics_path_planned"] == run.expected_outputs["metrics_path_planned"]


def test_detects_predictions_path_planned(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert (
        evaluation.planned_output_summary["predictions_path_planned"]
        == run.expected_outputs["predictions_path_planned"]
    )


def test_detects_run_dir_planned(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert evaluation.planned_output_summary["run_dir_planned"] == run.expected_outputs["run_dir_planned"]


def test_creates_planned_records_for_expected_outputs(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    kinds = {record.artifact_kind for record in evaluation.artifact_records}
    assert DetectionTrainingArtifactKind.PLANNED_WEIGHTS in kinds
    assert DetectionTrainingArtifactKind.PLANNED_METRICS in kinds
    assert DetectionTrainingArtifactKind.PLANNED_PREDICTIONS in kinds
    assert DetectionTrainingArtifactKind.PLANNED_RUN_DIR in kinds
    assert all(record.artifact_state.value == "planned" for record in evaluation.artifact_records)


def test_blocks_if_artifact_root_dir_required_and_missing(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=None, require_artifact_root_dir=True)

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "output_dir_missing" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_MISSING_OUTPUT_DIR


def test_blocks_if_artifact_root_dir_inside_repo_and_not_allowed(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    inside_dir = _REPO_ROOT / "some_test_artifact_dir"
    config = DetectionTrainingArtifactPolicyConfig(
        artifact_root_dir=str(inside_dir), allow_artifacts_inside_repo=False
    )

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "output_dir_inside_repo" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_REPO_STORAGE


def test_blocks_if_planned_weight_points_inside_repo(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    inside_root = str(_REPO_ROOT / "some_test_artifact_dir")
    run = _planned_run(bundle, artifact_root=inside_root)
    env_spec = _environment_spec(run, bundle)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=inside_root, allow_artifacts_inside_repo=True)

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "model_weight_in_repo_not_allowed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_FORBIDDEN_EXTENSION


def test_allows_planned_weight_outside_repo(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert not any(issue.code == "model_weight_in_repo_not_allowed" for issue in evaluation.issues)


def test_warning_if_gitignore_missing(tmp_path, monkeypatch):
    import blueberry_microid.application.services.detection_training_artifact_policy_evaluator as evaluator_module

    monkeypatch.setattr(evaluator_module.DetectionTrainingArtifactPolicyEvaluator, "_repo_root", staticmethod(lambda: tmp_path / "no_such_repo"))
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "gitignore_missing" for issue in evaluation.warnings)


def test_warning_if_gitignore_missing_weight_patterns(tmp_path, monkeypatch):
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    (fake_repo / ".gitignore").write_text("*.pyc\n", encoding="utf-8")

    import blueberry_microid.application.services.detection_training_artifact_policy_evaluator as evaluator_module

    monkeypatch.setattr(
        evaluator_module.DetectionTrainingArtifactPolicyEvaluator, "_repo_root", staticmethod(lambda: fake_repo)
    )
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "gitignore_does_not_exclude_weights" for issue in evaluation.warnings)


def test_does_not_modify_gitignore(tmp_path, monkeypatch):
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    gitignore_path = fake_repo / ".gitignore"
    gitignore_path.write_text("*.pyc\n", encoding="utf-8")

    import blueberry_microid.application.services.detection_training_artifact_policy_evaluator as evaluator_module

    monkeypatch.setattr(
        evaluator_module.DetectionTrainingArtifactPolicyEvaluator, "_repo_root", staticmethod(lambda: fake_repo)
    )
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    _evaluate(run, bundle, files, env_spec, config=config)

    assert gitignore_path.read_text(encoding="utf-8") == "*.pyc\n"


def test_does_not_write_files(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))
    before = set(tmp_path.rglob("*"))

    _evaluate(run, bundle, files, env_spec, config=config)

    after = set(tmp_path.rglob("*"))
    assert before == after


def test_does_not_compute_checksum_of_planned_artifact(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert all(record.checksum_sha256 is None for record in evaluation.artifact_records)


def test_blocks_actual_artifact_if_not_allowed(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(
        artifact_root_dir=str(tmp_path / "artifacts"),
        register_actual_artifacts=True,
        allow_actual_artifact_registration=False,
    )

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "actual_artifact_registration_not_allowed_yet" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_POLICY_VIOLATION


def test_metadata_extensions_allowed(tmp_path):
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))
    assert ".json" in config.allowed_metadata_extensions
    assert ".yaml" in config.allowed_metadata_extensions


def test_generates_storage_policy(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert "artifact_root_dir" in evaluation.storage_policy
    assert "forbidden_extensions" in evaluation.storage_policy


def test_generates_git_policy(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert evaluation.git_policy["gitignore_modified"] is False
    assert "required_gitignore_patterns" in evaluation.git_policy


def test_generates_checksum_policy(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert evaluation.checksum_policy["checksums_computed"] is False
    assert evaluation.checksum_policy["checksum_algorithm"] == "sha256"


def test_generates_registry_summary(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert evaluation.registry_summary["planned_record_count"] == len(evaluation.artifact_records)
    assert evaluation.registry_summary["actual_record_count"] == 0


def test_issue_no_training_executed_always_present(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "no_training_executed" for issue in evaluation.infos)


def test_issue_planned_artifact_only_for_planned_weights(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    assert any(issue.code == "planned_artifact_only" for issue in evaluation.infos)


def test_does_not_import_torch(tmp_path):
    import sys

    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))
    _evaluate(run, bundle, files, env_spec, config=config)

    assert "torch" not in sys.modules


def test_does_not_import_ultralytics(tmp_path):
    import sys

    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))
    _evaluate(run, bundle, files, env_spec, config=config)

    assert "ultralytics" not in sys.modules


def test_does_not_execute_commands(tmp_path, monkeypatch):
    import subprocess

    def _fail(*args, **kwargs):
        raise AssertionError("subprocess must never be invoked by the artifact policy evaluator")

    monkeypatch.setattr(subprocess, "run", _fail)
    monkeypatch.setattr(subprocess, "Popen", _fail)

    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))
    _evaluate(run, bundle, files, env_spec, config=config)


def test_does_not_create_weights(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    _evaluate(run, bundle, files, env_spec, config=config)

    assert not list(tmp_path.rglob("*.pt"))
    assert not list(tmp_path.rglob("*.onnx"))
    assert not list(tmp_path.rglob("*.h5"))


def test_does_not_download_anything(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(
        artifact_root_dir=str(tmp_path / "artifacts"), allow_external_uri=True
    )

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    haystack = str(evaluation.storage_policy).lower() + str(evaluation.registry_summary).lower()
    for word in _FORBIDDEN_WORDS:
        assert word not in haystack


def test_never_mentions_forbidden_terms(tmp_path):
    run, bundle, files, env_spec = _setup(tmp_path)
    config = DetectionTrainingArtifactPolicyConfig(artifact_root_dir=str(tmp_path / "artifacts"))

    evaluation = _evaluate(run, bundle, files, env_spec, config=config)

    haystack = (
        str(evaluation.storage_policy).lower()
        + str(evaluation.git_policy).lower()
        + str(evaluation.checksum_policy).lower()
        + str(evaluation.registry_summary).lower()
        + str(evaluation.risk_summary).lower()
        + str(evaluation.recommendation_summary).lower()
        + " ".join(str(issue.code) + str(issue.message) for issue in evaluation.issues).lower()
    )
    for word in _FORBIDDEN_WORDS:
        assert word not in haystack
