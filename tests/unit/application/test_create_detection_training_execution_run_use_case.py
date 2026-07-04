from uuid import uuid4

import pytest

from blueberry_microid.application.dto.detection_training_execution_dto import (
    CreateDetectionTrainingExecutionRunRequest,
    DetectionTrainingExecutionConfigDTO,
)
from blueberry_microid.application.exceptions import (
    DetectionTrainingArtifactPolicyNotFoundError,
    DetectionTrainingEnvironmentSpecNotFoundError,
    DetectionTrainingExecutionRunNotAllowedError,
    DetectionTrainingReadinessReportNotFoundError,
    DetectionTrainingRunNotFoundError,
)
from blueberry_microid.application.services.detection_training_execution_gate_evaluator import (
    DetectionTrainingExecutionGateEvaluator,
)
from blueberry_microid.application.services.manual_yolo_training_runner_scaffold import (
    ManualYoloTrainingRunnerScaffold,
)
from blueberry_microid.application.use_cases.detection_training_execution.create_detection_training_execution_run import (
    CreateDetectionTrainingExecutionRunUseCase,
)
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus
from tests.unit.application.fakes import (
    FailingAddDetectionTrainingExecutionIssueRepository,
    FakeUnitOfWork,
    InMemoryDetectionTrainingArtifactPolicyRepository,
    InMemoryDetectionTrainingEnvironmentSpecRepository,
    InMemoryDetectionTrainingExecutionIssueRepository,
    InMemoryDetectionTrainingExecutionRunRepository,
    InMemoryDetectionTrainingReadinessReportRepository,
    InMemoryDetectionTrainingRunRepository,
)
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle
from tests.unit.application.test_create_detection_training_environment_spec_use_case import _readiness_report
from tests.unit.application.test_detection_training_execution_gate_evaluator import (
    _artifact_policy,
    _environment_spec,
    _planned_run,
)

_REQUIRED_CONFIRMATION_TEXT = "I understand this will only create a scaffold and will not train a model"


def _build_use_case():
    run_repo = InMemoryDetectionTrainingRunRepository()
    readiness_repo = InMemoryDetectionTrainingReadinessReportRepository()
    environment_repo = InMemoryDetectionTrainingEnvironmentSpecRepository()
    artifact_policy_repo = InMemoryDetectionTrainingArtifactPolicyRepository()
    execution_run_repo = InMemoryDetectionTrainingExecutionRunRepository()
    execution_issue_repo = InMemoryDetectionTrainingExecutionIssueRepository()
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        detection_training_execution_run_repository=execution_run_repo,
        detection_training_execution_issue_repository=execution_issue_repo,
    )
    use_case = CreateDetectionTrainingExecutionRunUseCase(
        run_repo,
        readiness_repo,
        environment_repo,
        artifact_policy_repo,
        DetectionTrainingExecutionGateEvaluator(),
        ManualYoloTrainingRunnerScaffold(),
        uow,
    )
    return use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, execution_run_repo, execution_issue_repo


def _seed(tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo):
    bundle, _ = _completed_bundle(tmp_path)
    run = _planned_run(bundle)
    run_repo.add(run)
    readiness = _readiness_report(run, bundle)
    readiness_repo.add(readiness)
    environment_spec = _environment_spec(run, bundle, readiness)
    environment_repo.add(environment_spec)
    artifact_policy = _artifact_policy(run, readiness, environment_spec, bundle)
    artifact_policy_repo.add(artifact_policy)
    return bundle, run, readiness, environment_spec, artifact_policy


def test_creates_manual_required_execution_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
            config=DetectionTrainingExecutionConfigDTO(block_in_ci=False),
        )
    )

    assert dto.status == DetectionTrainingExecutionStatus.MANUAL_REQUIRED
    assert dto.is_executable is False


def test_creates_blocked_execution_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
            config=DetectionTrainingExecutionConfigDTO(block_in_ci=False, enable_real_training=True),
        )
    )

    assert dto.status == DetectionTrainingExecutionStatus.BLOCKED


def test_creates_ready_to_execute_when_config_allows(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
            config=DetectionTrainingExecutionConfigDTO(
                block_in_ci=False,
                manual_confirmation_text=_REQUIRED_CONFIRMATION_TEXT,
                allow_ready_to_execute_status=True,
            ),
        )
    )

    assert dto.status == DetectionTrainingExecutionStatus.READY_TO_EXECUTE
    assert dto.is_executable is False


def test_persists_issues(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, execution_issue_repo = (
        _build_use_case()
    )
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
            config=DetectionTrainingExecutionConfigDTO(block_in_ci=False),
        )
    )

    issues = execution_issue_repo.list_by_execution_run_id(dto.id)
    assert len(issues) > 0
    assert any(issue.code == "no_training_executed" for issue in issues)


def test_persists_execution_plan(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
            config=DetectionTrainingExecutionConfigDTO(block_in_ci=False),
        )
    )

    assert "manual_steps" in dto.execution_plan
    assert "prohibited_actions" in dto.execution_plan


def test_verifies_readiness_belongs_to_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    other_bundle, _ = _completed_bundle(tmp_path / "other")
    other_run = _planned_run(other_bundle)
    run_repo.add(other_run)

    with pytest.raises(DetectionTrainingExecutionRunNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=other_run.id,
                readiness_report_id=readiness.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=artifact_policy.id,
            )
        )


def test_verifies_environment_spec_belongs_to_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    other_bundle, _ = _completed_bundle(tmp_path / "other")
    other_run = _planned_run(other_bundle)
    run_repo.add(other_run)
    other_readiness = _readiness_report(other_run, other_bundle)
    readiness_repo.add(other_readiness)

    with pytest.raises(DetectionTrainingExecutionRunNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=other_run.id,
                readiness_report_id=other_readiness.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=artifact_policy.id,
            )
        )


def test_verifies_environment_spec_belongs_to_readiness_report(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    other_readiness = _readiness_report(run, bundle)
    readiness_repo.add(other_readiness)

    with pytest.raises(DetectionTrainingExecutionRunNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=run.id,
                readiness_report_id=other_readiness.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=artifact_policy.id,
            )
        )


def test_verifies_artifact_policy_belongs_to_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    other_bundle, _ = _completed_bundle(tmp_path / "other")
    other_run = _planned_run(other_bundle)
    run_repo.add(other_run)
    other_readiness = _readiness_report(other_run, other_bundle)
    readiness_repo.add(other_readiness)
    other_environment = _environment_spec(other_run, other_bundle, other_readiness)
    environment_repo.add(other_environment)

    with pytest.raises(DetectionTrainingExecutionRunNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=other_run.id,
                readiness_report_id=other_readiness.id,
                environment_spec_id=other_environment.id,
                artifact_policy_id=artifact_policy.id,
            )
        )


def test_verifies_artifact_policy_belongs_to_readiness_report(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    other_readiness = _readiness_report(run, bundle)
    readiness_repo.add(other_readiness)
    other_environment = _environment_spec(run, bundle, other_readiness)
    environment_repo.add(other_environment)
    other_artifact_policy = _artifact_policy(run, other_readiness, other_environment, bundle)
    artifact_policy_repo.add(other_artifact_policy)

    with pytest.raises(DetectionTrainingExecutionRunNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=run.id,
                readiness_report_id=readiness.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=other_artifact_policy.id,
            )
        )


def test_verifies_artifact_policy_belongs_to_environment_spec(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    other_environment = _environment_spec(run, bundle, readiness)
    environment_repo.add(other_environment)
    other_artifact_policy = _artifact_policy(run, readiness, other_environment, bundle)
    artifact_policy_repo.add(other_artifact_policy)

    with pytest.raises(DetectionTrainingExecutionRunNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=run.id,
                readiness_report_id=readiness.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=other_artifact_policy.id,
            )
        )


def test_does_not_modify_detection_training_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    original_status = run.status

    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert run_repo.get_by_id(run.id).status == original_status


def test_does_not_modify_readiness_report(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    original_status = readiness.status

    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert readiness_repo.get_by_id(readiness.id).status == original_status


def test_does_not_modify_environment_spec(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    original_status = environment_spec.status

    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert environment_repo.get_by_id(environment_spec.id).status == original_status


def test_does_not_modify_artifact_policy(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    original_status = artifact_policy.status

    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert artifact_policy_repo.get_by_id(artifact_policy.id).status == original_status


def test_rollback_if_issue_persistence_fails(tmp_path):
    run_repo = InMemoryDetectionTrainingRunRepository()
    readiness_repo = InMemoryDetectionTrainingReadinessReportRepository()
    environment_repo = InMemoryDetectionTrainingEnvironmentSpecRepository()
    artifact_policy_repo = InMemoryDetectionTrainingArtifactPolicyRepository()
    execution_run_repo = InMemoryDetectionTrainingExecutionRunRepository()
    delegate = InMemoryDetectionTrainingExecutionIssueRepository()
    failing_issue_repo = FailingAddDetectionTrainingExecutionIssueRepository(delegate)
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        detection_training_execution_run_repository=execution_run_repo,
        detection_training_execution_issue_repository=failing_issue_repo,
    )
    use_case = CreateDetectionTrainingExecutionRunUseCase(
        run_repo,
        readiness_repo,
        environment_repo,
        artifact_policy_repo,
        DetectionTrainingExecutionGateEvaluator(),
        ManualYoloTrainingRunnerScaffold(),
        uow,
    )
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=run.id,
                readiness_report_id=readiness.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=artifact_policy.id,
            )
        )

    assert execution_run_repo.list_all() == []


def test_raises_not_found_for_missing_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    with pytest.raises(DetectionTrainingRunNotFoundError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=uuid4(),
                readiness_report_id=readiness.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=artifact_policy.id,
            )
        )


def test_raises_not_found_for_missing_readiness_report(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    with pytest.raises(DetectionTrainingReadinessReportNotFoundError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=run.id,
                readiness_report_id=uuid4(),
                environment_spec_id=environment_spec.id,
                artifact_policy_id=artifact_policy.id,
            )
        )


def test_raises_not_found_for_missing_environment_spec(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    with pytest.raises(DetectionTrainingEnvironmentSpecNotFoundError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=run.id,
                readiness_report_id=readiness.id,
                environment_spec_id=uuid4(),
                artifact_policy_id=artifact_policy.id,
            )
        )


def test_raises_not_found_for_missing_artifact_policy(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, _, _ = _build_use_case()
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )

    with pytest.raises(DetectionTrainingArtifactPolicyNotFoundError):
        use_case.execute(
            CreateDetectionTrainingExecutionRunRequest(
                detection_training_run_id=run.id,
                readiness_report_id=readiness.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=uuid4(),
            )
        )


def test_lists_execution_runs_by_detection_training_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, execution_run_repo, _ = (
        _build_use_case()
    )
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert len(execution_run_repo.list_by_detection_training_run_id(run.id)) == 1


def test_lists_execution_runs_by_readiness_report(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, execution_run_repo, _ = (
        _build_use_case()
    )
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert len(execution_run_repo.list_by_readiness_report_id(readiness.id)) == 1


def test_lists_execution_runs_by_environment_spec(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, execution_run_repo, _ = (
        _build_use_case()
    )
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert len(execution_run_repo.list_by_environment_spec_id(environment_spec.id)) == 1


def test_lists_execution_runs_by_artifact_policy(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, execution_run_repo, _ = (
        _build_use_case()
    )
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert len(execution_run_repo.list_by_artifact_policy_id(artifact_policy.id)) == 1


def test_lists_execution_runs_by_annotation_bundle_run(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, execution_run_repo, _ = (
        _build_use_case()
    )
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert len(execution_run_repo.list_by_annotation_bundle_run_id(run.annotation_bundle_run_id)) == 1


def test_lists_execution_runs_by_dataset_release(tmp_path):
    use_case, run_repo, readiness_repo, environment_repo, artifact_policy_repo, execution_run_repo, _ = (
        _build_use_case()
    )
    bundle, run, readiness, environment_spec, artifact_policy = _seed(
        tmp_path, run_repo, readiness_repo, environment_repo, artifact_policy_repo
    )
    use_case.execute(
        CreateDetectionTrainingExecutionRunRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=environment_spec.id,
            artifact_policy_id=artifact_policy.id,
        )
    )

    assert len(execution_run_repo.list_by_dataset_release_id(run.dataset_release_id)) == 1
