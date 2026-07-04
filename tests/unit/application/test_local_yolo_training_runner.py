from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from blueberry_microid.application.services.local_yolo_training_runner import (
    LocalYoloTrainingRunner,
    LocalYoloTrainingRunnerError,
)
from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.detection_training_artifact_policy import DetectionTrainingArtifactPolicy
from blueberry_microid.domain.entities.detection_training_execution_run import DetectionTrainingExecutionRun
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.domain.enums.detection_training_artifact_kind import DetectionTrainingArtifactKind
from blueberry_microid.domain.enums.detection_training_artifact_policy_decision import (
    DetectionTrainingArtifactPolicyDecision,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_status import (
    DetectionTrainingArtifactPolicyStatus,
)
from blueberry_microid.domain.enums.detection_training_execution_decision import DetectionTrainingExecutionDecision
from blueberry_microid.domain.enums.detection_training_execution_mode import DetectionTrainingExecutionMode
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus
from blueberry_microid.ml.configs.local_yolo_training_runner_config import LocalYoloTrainingRunnerConfig
from blueberry_microid.ml.configs.training_safety_defaults import default_required_gitignore_patterns

_CONFIRMATION = "I understand this will run local YOLO training outside CI"
_SOURCE = Path("src/blueberry_microid/application/services/local_yolo_training_runner.py")


def _execution_run(policy_id, bundle_id, training_run_id=None, *, status=DetectionTrainingExecutionStatus.READY_TO_EXECUTE):
    return DetectionTrainingExecutionRun(
        detection_training_run_id=training_run_id or uuid4(),
        readiness_report_id=uuid4(),
        environment_spec_id=uuid4(),
        artifact_policy_id=policy_id,
        annotation_bundle_run_id=bundle_id,
        dataset_release_id=uuid4(),
        status=status,
        decision=DetectionTrainingExecutionDecision.READY_FOR_MANUAL_EXECUTION,
        mode=DetectionTrainingExecutionMode.MANUAL_GATE,
        is_executable=False,
        config={},
        prerequisite_summary={},
        repository_safety_summary={},
        execution_plan={},
        command_preview={"command": "yolo detect train"},
        expected_outputs={},
        risk_summary={},
        recommendation_summary={},
        error_count=0,
        warning_count=0,
        info_count=1,
    )


def _policy(policy_id, training_run_id, artifact_root, *, ready=True, allow_actual=True):
    return DetectionTrainingArtifactPolicy(
        id=policy_id,
        detection_training_run_id=training_run_id,
        readiness_report_id=uuid4(),
        environment_spec_id=uuid4(),
        annotation_bundle_run_id=uuid4(),
        dataset_release_id=uuid4(),
        decision=DetectionTrainingArtifactPolicyDecision.ARTIFACT_POLICY_READY,
        status=DetectionTrainingArtifactPolicyStatus.READY if ready else DetectionTrainingArtifactPolicyStatus.BLOCKED,
        is_policy_ready=ready,
        config={
            "allow_actual_artifact_registration": allow_actual,
            "register_actual_artifacts": allow_actual,
        },
        planned_output_summary={},
        storage_policy={"artifact_root_dir_inside_repo": False},
        git_policy={},
        checksum_policy={"checksum_algorithm": "sha256"},
        registry_summary={},
        risk_summary={},
        recommendation_summary={},
        error_count=0 if ready else 1,
        warning_count=0,
        info_count=0,
        artifact_root_dir=str(artifact_root),
    )


def _bundle_file(bundle_id, dataset_yaml):
    return AnnotationBundleFile(
        bundle_run_id=bundle_id,
        file_role=AnnotationBundleFileRole.DATASET_YAML,
        file_path=str(dataset_yaml),
        relative_path="dataset.yaml",
    )


def _config(artifact_root, base_model, **overrides):
    values = {
        "manual_confirmation_text": _CONFIRMATION,
        "artifact_root_dir": str(artifact_root),
        "base_model_path": str(base_model),
        "run_name": "manual-run",
        "epochs": 1,
        "image_size": 32,
        "batch_size": 1,
        "workers": 0,
    }
    values.update(overrides)
    return LocalYoloTrainingRunnerConfig(**values)


class _FakeYolo:
    calls = []

    def __init__(self, model_path):
        self.model_path = model_path

    def train(self, **kwargs):
        self.calls.append({"model_path": self.model_path, "kwargs": kwargs})
        save_dir = Path(kwargs["project"]) / kwargs["name"]
        weights_dir = save_dir / "weights"
        weights_dir.mkdir(parents=True)
        (weights_dir / "best.pt").write_bytes(b"fake-weights")
        (save_dir / "results.csv").write_text("epoch,metric\n1,0.1\n", encoding="utf-8")
        (save_dir / "train.log").write_text("ok\n", encoding="utf-8")
        (save_dir / "args.yaml").write_text("epochs: 1\n", encoding="utf-8")
        return SimpleNamespace(save_dir=str(save_dir))


def _setup(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".gitignore").write_text(
        "\n".join(default_required_gitignore_patterns()) + "\n", encoding="utf-8"
    )
    artifact_root = tmp_path / "artifacts"
    base_model = tmp_path / "base-model.pt"
    base_model.write_bytes(b"local-base")
    dataset_yaml = tmp_path / "bundle" / "dataset.yaml"
    dataset_yaml.parent.mkdir()
    dataset_yaml.write_text("path: .\ntrain: images\nval: images\nnames: [candidate_region]\n", encoding="utf-8")
    policy_id = uuid4()
    bundle_id = uuid4()
    execution_run = _execution_run(policy_id, bundle_id)
    policy = _policy(policy_id, execution_run.detection_training_run_id, artifact_root)
    return repo_root, artifact_root, base_model, dataset_yaml, execution_run, policy, [_bundle_file(bundle_id, dataset_yaml)]


def test_runs_local_yolo_and_returns_metadata_only_records(tmp_path, monkeypatch):
    repo_root, artifact_root, base_model, _, execution_run, policy, bundle_files = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    _FakeYolo.calls = []

    result = LocalYoloTrainingRunner(repo_root=repo_root, yolo_class_factory=lambda: _FakeYolo).run(
        execution_run=execution_run,
        artifact_policy=policy,
        bundle_files=bundle_files,
        config=_config(artifact_root, base_model),
    )

    assert _FakeYolo.calls[0]["kwargs"]["data"].endswith("dataset.yaml")
    assert result.summary["metadata_only"] is True
    assert result.summary["no_binary_content_stored"] is True
    assert {record.artifact_kind for record in result.records} >= {
        DetectionTrainingArtifactKind.ACTUAL_WEIGHTS,
        DetectionTrainingArtifactKind.ACTUAL_METRICS,
        DetectionTrainingArtifactKind.ACTUAL_LOGS,
    }
    weight_record = next(record for record in result.records if record.artifact_kind == DetectionTrainingArtifactKind.ACTUAL_WEIGHTS)
    assert weight_record.checksum_sha256
    assert weight_record.size_bytes == len(b"fake-weights")
    assert weight_record.metadata["training_execution_run_id"] == str(execution_run.id)


def test_blocks_in_ci_before_importing_ultralytics(tmp_path, monkeypatch):
    repo_root, artifact_root, base_model, _, execution_run, policy, bundle_files = _setup(tmp_path)
    monkeypatch.setenv("CI", "true")

    with pytest.raises(LocalYoloTrainingRunnerError, match="blocked in CI"):
        LocalYoloTrainingRunner(
            repo_root=repo_root,
            yolo_class_factory=lambda: pytest.fail("ultralytics must not load in CI"),
        ).run(
            execution_run=execution_run,
            artifact_policy=policy,
            bundle_files=bundle_files,
            config=_config(artifact_root, base_model),
        )


def test_requires_exact_manual_confirmation_before_importing_ultralytics(tmp_path, monkeypatch):
    repo_root, artifact_root, base_model, _, execution_run, policy, bundle_files = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    with pytest.raises(LocalYoloTrainingRunnerError, match="manual confirmation"):
        LocalYoloTrainingRunner(
            repo_root=repo_root,
            yolo_class_factory=lambda: pytest.fail("ultralytics must not load without confirmation"),
        ).run(
            execution_run=execution_run,
            artifact_policy=policy,
            bundle_files=bundle_files,
            config=_config(artifact_root, base_model, manual_confirmation_text="yes"),
        )


def test_blocks_when_execution_run_is_not_ready(tmp_path, monkeypatch):
    repo_root, artifact_root, base_model, _, execution_run, policy, bundle_files = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    execution_run.status = DetectionTrainingExecutionStatus.MANUAL_REQUIRED

    with pytest.raises(LocalYoloTrainingRunnerError, match="ready_to_execute"):
        LocalYoloTrainingRunner(repo_root=repo_root, yolo_class_factory=lambda: _FakeYolo).run(
            execution_run=execution_run,
            artifact_policy=policy,
            bundle_files=bundle_files,
            config=_config(artifact_root, base_model),
        )


def test_blocks_when_policy_does_not_allow_actual_registration(tmp_path, monkeypatch):
    repo_root, artifact_root, base_model, _, execution_run, policy, bundle_files = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    policy.config["register_actual_artifacts"] = False

    with pytest.raises(LocalYoloTrainingRunnerError, match="does not allow actual"):
        LocalYoloTrainingRunner(repo_root=repo_root, yolo_class_factory=lambda: _FakeYolo).run(
            execution_run=execution_run,
            artifact_policy=policy,
            bundle_files=bundle_files,
            config=_config(artifact_root, base_model),
        )


def test_blocks_artifact_root_inside_repository(tmp_path, monkeypatch):
    repo_root, _, base_model, _, execution_run, policy, bundle_files = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    inside_root = repo_root / "runs"
    policy.artifact_root_dir = str(inside_root)

    with pytest.raises(LocalYoloTrainingRunnerError, match="outside the repository"):
        LocalYoloTrainingRunner(repo_root=repo_root, yolo_class_factory=lambda: _FakeYolo).run(
            execution_run=execution_run,
            artifact_policy=policy,
            bundle_files=bundle_files,
            config=_config(inside_root, base_model),
        )


def test_blocks_base_model_inside_repository(tmp_path, monkeypatch):
    repo_root, artifact_root, _, _, execution_run, policy, bundle_files = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    base_model = repo_root / "best.pt"
    base_model.write_bytes(b"bad")

    with pytest.raises(LocalYoloTrainingRunnerError, match="base_model_path must be outside"):
        LocalYoloTrainingRunner(repo_root=repo_root, yolo_class_factory=lambda: _FakeYolo).run(
            execution_run=execution_run,
            artifact_policy=policy,
            bundle_files=bundle_files,
            config=_config(artifact_root, base_model),
        )


def test_requires_dataset_yaml_from_bundle(tmp_path, monkeypatch):
    repo_root, artifact_root, base_model, _, execution_run, policy, _ = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    with pytest.raises(LocalYoloTrainingRunnerError, match="no dataset_yaml"):
        LocalYoloTrainingRunner(repo_root=repo_root, yolo_class_factory=lambda: _FakeYolo).run(
            execution_run=execution_run,
            artifact_policy=policy,
            bundle_files=[],
            config=_config(artifact_root, base_model),
        )


def test_runner_does_not_import_subprocess_or_ultralytics_at_module_level():
    source = _SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [
        (node.module if isinstance(node, ast.ImportFrom) else alias.name)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    ]

    assert "subprocess" not in imports
    assert "ultralytics" not in imports
