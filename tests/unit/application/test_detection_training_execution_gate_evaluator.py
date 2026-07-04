import ast
import inspect

from blueberry_microid.application.services.detection_training_execution_gate_evaluator import (
    DetectionTrainingExecutionGateEvaluator,
)
from blueberry_microid.domain.entities.detection_training_artifact_policy import DetectionTrainingArtifactPolicy
from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec
from blueberry_microid.domain.entities.detection_training_readiness_report import DetectionTrainingReadinessReport
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
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
from blueberry_microid.domain.enums.detection_training_execution_decision import DetectionTrainingExecutionDecision
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_execution_config import DetectionTrainingExecutionConfig
from blueberry_microid.ml.reports.repository_safety_report import RepositorySafetyReport
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle

_REQUIRED_CONFIRMATION_TEXT = "I understand this will only create a scaffold and will not train a model"
_FORBIDDEN_WORDS = ("bacteria", "fungi", "colony", "species", "genus", "taxon", "diagnosis")


def _planned_run(bundle, *, status=DetectionTrainingStatus.PLANNED, is_runnable=True, command_preview=None, expected_outputs=None):
    return DetectionTrainingRun(
        annotation_bundle_run_id=bundle.id,
        dataset_release_id=bundle.dataset_release_id,
        petri_annotation_export_run_id=bundle.petri_annotation_export_run_id,
        annotation_quality_gate_run_id=None,
        algorithm=DetectionTrainingAlgorithm.YOLO_DRY_RUN,
        mode=DetectionTrainingMode.DRY_RUN,
        status=status,
        is_runnable=is_runnable,
        config={},
        training_plan={"planned": True},
        command_preview=command_preview if command_preview is not None else {"command": "yolo detect train ..."},
        dataset_summary={},
        quality_gate_summary={},
        expected_outputs=expected_outputs if expected_outputs is not None else {"weights_path_planned": "/tmp/out/best.pt"},
        issue_count=0,
        warning_count=0,
        error_count=0 if status == DetectionTrainingStatus.PLANNED else 1,
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


def _environment_spec(
    run,
    bundle,
    readiness,
    *,
    status=DetectionTrainingEnvironmentStatus.READY,
    decision=DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY,
    error_count=0,
    is_environment_ready=True,
):
    return DetectionTrainingEnvironmentSpec(
        detection_training_run_id=run.id,
        readiness_report_id=readiness.id,
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


def _artifact_policy(
    run,
    readiness,
    environment_spec,
    bundle,
    *,
    status=DetectionTrainingArtifactPolicyStatus.READY,
    decision=DetectionTrainingArtifactPolicyDecision.ARTIFACT_POLICY_READY,
    error_count=0,
    is_policy_ready=True,
    storage_policy=None,
):
    return DetectionTrainingArtifactPolicy(
        detection_training_run_id=run.id,
        readiness_report_id=readiness.id,
        environment_spec_id=environment_spec.id,
        annotation_bundle_run_id=bundle.id,
        dataset_release_id=bundle.dataset_release_id,
        decision=decision,
        status=status,
        is_policy_ready=is_policy_ready,
        config={},
        artifact_root_dir="/tmp/blueberry-artifacts",
        planned_output_summary={},
        storage_policy=storage_policy if storage_policy is not None else {"artifact_root_dir_inside_repo": False},
        git_policy={},
        checksum_policy={},
        registry_summary={},
        risk_summary={},
        recommendation_summary={},
        error_count=error_count,
        warning_count=0,
        info_count=0,
    )


def _safe_report(is_safe=True, path_violations=None):
    return RepositorySafetyReport(
        is_safe=is_safe,
        gitignore_exists=True,
        missing_gitignore_patterns=[] if is_safe else ["*.pt"],
        path_violations=path_violations or [],
    )


def _setup(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    run = _planned_run(bundle)
    readiness = _readiness_report(run, bundle)
    environment_spec = _environment_spec(run, bundle, readiness)
    artifact_policy = _artifact_policy(run, readiness, environment_spec, bundle)
    return bundle, run, readiness, environment_spec, artifact_policy


def _evaluate(run, readiness, environment_spec, artifact_policy, *, repository_safety=None, config=None):
    evaluator = DetectionTrainingExecutionGateEvaluator()
    return evaluator.evaluate(
        run,
        readiness,
        environment_spec,
        artifact_policy,
        repository_safety or _safe_report(),
        config or DetectionTrainingExecutionConfig(block_in_ci=False),
    )


def test_blocks_if_run_not_planned(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    run = _planned_run(bundle, status=DetectionTrainingStatus.BLOCKED, is_runnable=False)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "detection_training_not_planned" for issue in evaluation.errors)


def test_blocks_if_not_runnable(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    run = _planned_run(bundle, status=DetectionTrainingStatus.BLOCKED, is_runnable=False)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "detection_training_not_planned" for issue in evaluation.errors)


def test_blocks_if_command_preview_missing(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    run = _planned_run(bundle, command_preview={})

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "command_preview_missing" for issue in evaluation.errors)


def test_blocks_if_expected_outputs_missing(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    run = _planned_run(bundle, expected_outputs={})

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "expected_outputs_missing" for issue in evaluation.errors)


def test_blocks_if_readiness_not_ready(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    readiness = _readiness_report(
        run,
        bundle,
        status=DetectionTrainingReadinessStatus.BLOCKED,
        decision=DetectionTrainingReadinessDecision.BLOCKED_BY_QUALITY,
        error_count=1,
        is_ready=False,
    )

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "readiness_not_ready" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingExecutionDecision.BLOCKED_BY_READINESS


def test_blocks_if_environment_not_ready(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    environment_spec = _environment_spec(
        run,
        bundle,
        readiness,
        status=DetectionTrainingEnvironmentStatus.BLOCKED,
        decision=DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS,
        error_count=1,
        is_environment_ready=False,
    )

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "environment_not_ready" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingExecutionDecision.BLOCKED_BY_ENVIRONMENT


def test_blocks_if_artifact_policy_not_ready(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    artifact_policy = _artifact_policy(
        run,
        readiness,
        environment_spec,
        bundle,
        status=DetectionTrainingArtifactPolicyStatus.BLOCKED,
        decision=DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_REPO_STORAGE,
        error_count=1,
        is_policy_ready=False,
    )

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "artifact_policy_not_ready" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingExecutionDecision.BLOCKED_BY_ARTIFACT_POLICY


def test_blocks_if_repository_safety_failed(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy, repository_safety=_safe_report(is_safe=False))

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "repository_safety_failed" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingExecutionDecision.BLOCKED_BY_REPOSITORY_SAFETY


def test_blocks_in_ci_when_block_in_ci_true(tmp_path, monkeypatch):
    monkeypatch.setenv("CI", "true")
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)

    evaluation = _evaluate(
        run, readiness, environment_spec, artifact_policy, config=DetectionTrainingExecutionConfig(block_in_ci=True)
    )

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "ci_execution_blocked" for issue in evaluation.errors)
    assert evaluation.decision == DetectionTrainingExecutionDecision.BLOCKED_BY_CI


def test_manual_required_if_confirmation_missing(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert evaluation.status == DetectionTrainingExecutionStatus.MANUAL_REQUIRED
    assert any(issue.code == "manual_confirmation_missing" for issue in evaluation.warnings)


def test_manual_required_if_confirmation_incorrect(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    config = DetectionTrainingExecutionConfig(block_in_ci=False, manual_confirmation_text="nope")

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy, config=config)

    assert evaluation.status == DetectionTrainingExecutionStatus.MANUAL_REQUIRED
    assert any(issue.code == "manual_confirmation_invalid" for issue in evaluation.warnings)


def test_manual_required_even_when_correct_if_allow_ready_false(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    config = DetectionTrainingExecutionConfig(
        block_in_ci=False,
        manual_confirmation_text=_REQUIRED_CONFIRMATION_TEXT,
        allow_ready_to_execute_status=False,
    )

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy, config=config)

    assert evaluation.status == DetectionTrainingExecutionStatus.MANUAL_REQUIRED


def test_ready_to_execute_when_everything_correct_and_allowed(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    config = DetectionTrainingExecutionConfig(
        block_in_ci=False,
        manual_confirmation_text=_REQUIRED_CONFIRMATION_TEXT,
        allow_ready_to_execute_status=True,
    )

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy, config=config)

    assert evaluation.status == DetectionTrainingExecutionStatus.READY_TO_EXECUTE
    assert evaluation.decision == DetectionTrainingExecutionDecision.READY_FOR_MANUAL_EXECUTION
    assert evaluation.is_executable is False


def test_blocks_if_enable_real_training_true(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    config = DetectionTrainingExecutionConfig(block_in_ci=False, enable_real_training=True)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy, config=config)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "training_execution_disabled" for issue in evaluation.errors)


def test_blocks_if_dry_run_only_false(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    config = DetectionTrainingExecutionConfig(block_in_ci=False, dry_run_only=False)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy, config=config)

    assert evaluation.status == DetectionTrainingExecutionStatus.BLOCKED
    assert any(issue.code == "training_execution_disabled" for issue in evaluation.errors)


def test_always_includes_no_training_executed_issue(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert any(issue.code == "no_training_executed" for issue in evaluation.infos)


def test_always_includes_real_runner_not_implemented_issue(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    assert any(issue.code == "real_runner_not_implemented" for issue in evaluation.infos)


def test_never_executes_commands(tmp_path):
    source = inspect.getsource(
        __import__(
            "blueberry_microid.application.services.detection_training_execution_gate_evaluator",
            fromlist=["DetectionTrainingExecutionGateEvaluator"],
        )
    )
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name != "subprocess" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module != "subprocess"


def test_never_imports_torch():
    source = inspect.getsource(
        __import__(
            "blueberry_microid.application.services.detection_training_execution_gate_evaluator",
            fromlist=["DetectionTrainingExecutionGateEvaluator"],
        )
    )
    assert "import torch" not in source


def test_never_imports_ultralytics():
    source = inspect.getsource(
        __import__(
            "blueberry_microid.application.services.detection_training_execution_gate_evaluator",
            fromlist=["DetectionTrainingExecutionGateEvaluator"],
        )
    )
    assert "import ultralytics" not in source


def test_does_not_write_files(tmp_path):
    before = list(tmp_path.rglob("*"))
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    before = list(tmp_path.rglob("*"))

    _evaluate(run, readiness, environment_spec, artifact_policy)

    after = list(tmp_path.rglob("*"))
    assert before == after


def test_does_not_create_weights(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)

    _evaluate(run, readiness, environment_spec, artifact_policy)

    assert not any(p.suffix == ".pt" for p in tmp_path.rglob("*"))


def test_never_mentions_forbidden_terms(tmp_path):
    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)

    evaluation = _evaluate(run, readiness, environment_spec, artifact_policy)

    haystack = (
        str(evaluation.prerequisite_summary).lower()
        + str(evaluation.risk_summary).lower()
        + str(evaluation.recommendation_summary).lower()
        + " ".join(f"{issue.code} {issue.message}".lower() for issue in evaluation.issues)
    )
    for word in _FORBIDDEN_WORDS:
        assert word not in haystack
