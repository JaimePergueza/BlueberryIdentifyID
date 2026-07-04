from __future__ import annotations

from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryAnnotationBundleFileRepository,
    InMemoryDetectionTrainingArtifactPolicyRepository,
    InMemoryDetectionTrainingArtifactRecordRepository,
    InMemoryDetectionTrainingExecutionRunRepository,
    InMemoryPredictionRepository,
)

from blueberry_microid.application.use_cases.detection_training_execution.run_local_yolo_training import (
    RunLocalYoloTrainingUseCase,
)
from blueberry_microid.ml.configs.local_yolo_training_runner_config import LocalYoloTrainingRunnerConfig
from tests.unit.application.test_local_yolo_training_runner import (
    _CONFIRMATION,
    _FakeYolo,
    _bundle_file,
    _config,
    _execution_run,
    _policy,
    _setup,
)
from blueberry_microid.application.services.local_yolo_training_runner import LocalYoloTrainingRunner


def test_use_case_runs_local_training_and_persists_metadata_records(tmp_path, monkeypatch):
    repo_root, artifact_root, base_model, dataset_yaml, execution_run, policy, _ = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    execution_repo = InMemoryDetectionTrainingExecutionRunRepository()
    policy_repo = InMemoryDetectionTrainingArtifactPolicyRepository()
    bundle_file_repo = InMemoryAnnotationBundleFileRepository()
    record_repo = InMemoryDetectionTrainingArtifactRecordRepository()
    execution_repo.add(execution_run)
    policy_repo.add(policy)
    bundle_file_repo.add_many([_bundle_file(execution_run.annotation_bundle_run_id, dataset_yaml)])

    use_case = RunLocalYoloTrainingUseCase(
        execution_run_repository=execution_repo,
        artifact_policy_repository=policy_repo,
        bundle_file_repository=bundle_file_repo,
        runner=LocalYoloTrainingRunner(repo_root=repo_root, yolo_class_factory=lambda: _FakeYolo),
        unit_of_work=FakeUnitOfWork(
            analysis_run_repository=InMemoryAnalysisRunRepository(),
            prediction_repository=InMemoryPredictionRepository(),
            detection_training_artifact_record_repository=record_repo,
        ),
    )

    result = use_case.execute(execution_run.id, _config(artifact_root, base_model))

    persisted = record_repo.list_by_artifact_policy_id(policy.id)
    assert len(persisted) == len(result.records)
    assert all(record.artifact_path for record in persisted)
    assert all(
        record.metadata["metadata_only"] is True
        for record in persisted
        if record.metadata and record.metadata.get("role") != "actual_run_dir"
    )


def test_use_case_validate_only_does_not_persist_metadata_records(tmp_path, monkeypatch):
    repo_root, artifact_root, base_model, dataset_yaml, execution_run, policy, _ = _setup(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    execution_repo = InMemoryDetectionTrainingExecutionRunRepository()
    policy_repo = InMemoryDetectionTrainingArtifactPolicyRepository()
    bundle_file_repo = InMemoryAnnotationBundleFileRepository()
    record_repo = InMemoryDetectionTrainingArtifactRecordRepository()
    execution_repo.add(execution_run)
    policy_repo.add(policy)
    bundle_file_repo.add_many([_bundle_file(execution_run.annotation_bundle_run_id, dataset_yaml)])

    use_case = RunLocalYoloTrainingUseCase(
        execution_run_repository=execution_repo,
        artifact_policy_repository=policy_repo,
        bundle_file_repository=bundle_file_repo,
        runner=LocalYoloTrainingRunner(
            repo_root=repo_root,
            yolo_class_factory=lambda: (_ for _ in ()).throw(AssertionError("YOLO must not load")),
        ),
        unit_of_work=FakeUnitOfWork(
            analysis_run_repository=InMemoryAnalysisRunRepository(),
            prediction_repository=InMemoryPredictionRepository(),
            detection_training_artifact_record_repository=record_repo,
        ),
    )

    result = use_case.validate_only(execution_run.id, _config(artifact_root, base_model))

    assert result.summary["validation_only"] is True
    assert record_repo.list_by_artifact_policy_id(policy.id) == []


def test_config_requires_manual_confirmation_text():
    try:
        LocalYoloTrainingRunnerConfig(
            manual_confirmation_text="",
            artifact_root_dir="C:/outside",
            base_model_path="C:/outside/base.pt",
        )
    except ValueError as exc:
        assert "manual_confirmation_text" in str(exc)
    else:
        raise AssertionError("expected LocalYoloTrainingRunnerConfig to reject blank confirmation")
