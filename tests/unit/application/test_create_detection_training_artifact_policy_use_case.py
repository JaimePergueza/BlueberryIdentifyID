from uuid import uuid4

import pytest

from blueberry_microid.application.dto.detection_training_artifact_dto import (
    CreateDetectionTrainingArtifactPolicyRequest,
    DetectionTrainingArtifactPolicyConfigDTO,
)
from blueberry_microid.application.exceptions import (
    DetectionTrainingArtifactPolicyNotAllowedError,
    DetectionTrainingEnvironmentSpecNotFoundError,
    DetectionTrainingReadinessReportNotFoundError,
    DetectionTrainingRunNotFoundError,
)
from blueberry_microid.application.services.detection_training_artifact_policy_evaluator import (
    DetectionTrainingArtifactPolicyEvaluator,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.create_detection_training_artifact_policy import (
    CreateDetectionTrainingArtifactPolicyUseCase,
)
from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec
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
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle
from tests.unit.application.fakes import (
    FailingAddDetectionTrainingArtifactIssueRepository,
    FailingAddDetectionTrainingArtifactRecordRepository,
    FakeUnitOfWork,
    InMemoryAnnotationBundleFileRepository,
    InMemoryAnnotationBundleRunRepository,
    InMemoryDetectionTrainingArtifactIssueRepository,
    InMemoryDetectionTrainingArtifactPolicyRepository,
    InMemoryDetectionTrainingArtifactRecordRepository,
    InMemoryDetectionTrainingEnvironmentSpecRepository,
    InMemoryDetectionTrainingReadinessReportRepository,
    InMemoryDetectionTrainingRunRepository,
)
from tests.unit.application.test_create_detection_training_environment_spec_use_case import _readiness_report


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


def _build_use_case(*, record_repository=None, issue_repository=None):
    bundle_run_repo = InMemoryAnnotationBundleRunRepository()
    bundle_file_repo = InMemoryAnnotationBundleFileRepository()
    run_repo = InMemoryDetectionTrainingRunRepository()
    readiness_report_repo = InMemoryDetectionTrainingReadinessReportRepository()
    environment_spec_repo = InMemoryDetectionTrainingEnvironmentSpecRepository()
    policy_repo = InMemoryDetectionTrainingArtifactPolicyRepository()
    record_repo = record_repository or InMemoryDetectionTrainingArtifactRecordRepository()
    issue_repo = issue_repository or InMemoryDetectionTrainingArtifactIssueRepository()
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        detection_training_artifact_policy_repository=policy_repo,
        detection_training_artifact_record_repository=record_repo,
        detection_training_artifact_issue_repository=issue_repo,
    )
    use_case = CreateDetectionTrainingArtifactPolicyUseCase(
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        DetectionTrainingArtifactPolicyEvaluator(),
        uow,
    )
    return (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        record_repo,
        issue_repo,
    )


def _seed(tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo, **env_overrides):
    bundle, files = _completed_bundle(tmp_path)
    bundle_run_repo.add(bundle)
    bundle_file_repo.add_many(files)
    run = _planned_run(bundle, artifact_root=str(tmp_path / "artifacts"))
    run_repo.add(run)
    readiness = _readiness_report(run, bundle)
    readiness_report_repo.add(readiness)
    env_spec = _environment_spec(run, bundle, readiness, **env_overrides)
    environment_spec_repo.add(env_spec)
    return run, bundle, files, readiness, env_spec


def test_creates_ready_policy(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=env_spec.id,
            config=DetectionTrainingArtifactPolicyConfigDTO(
                artifact_root_dir=str(tmp_path / "artifacts"), require_gitignore_rules=False
            ),
        )
    )

    assert dto.decision == DetectionTrainingArtifactPolicyDecision.ARTIFACT_POLICY_READY
    assert dto.is_policy_ready is True
    assert policy_repo.get_by_id(dto.id) is not None


def test_creates_warning_policy(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=env_spec.id,
            config=DetectionTrainingArtifactPolicyConfigDTO(artifact_root_dir=str(tmp_path / "artifacts")),
        )
    )

    assert dto.status != DetectionTrainingArtifactPolicyStatus.BLOCKED


def test_creates_blocked_policy(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        status=DetectionTrainingEnvironmentStatus.BLOCKED,
        decision=DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS,
        error_count=1,
        is_environment_ready=False,
    )

    dto = use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=env_spec.id,
        )
    )

    assert dto.status == DetectionTrainingArtifactPolicyStatus.BLOCKED
    assert dto.is_policy_ready is False


def test_persists_artifact_records(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        record_repo,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=env_spec.id,
            config=DetectionTrainingArtifactPolicyConfigDTO(artifact_root_dir=str(tmp_path / "artifacts")),
        )
    )

    records = record_repo.list_by_artifact_policy_id(dto.id)
    assert len(records) == 4
    assert all(record.artifact_policy_id == dto.id for record in records)


def test_persists_issues(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        issue_repo,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=env_spec.id,
            config=DetectionTrainingArtifactPolicyConfigDTO(artifact_root_dir=str(tmp_path / "artifacts")),
        )
    )

    issues = issue_repo.list_by_artifact_policy_id(dto.id)
    assert len(issues) > 0


def test_persists_summaries(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    dto = use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            environment_spec_id=env_spec.id,
            config=DetectionTrainingArtifactPolicyConfigDTO(artifact_root_dir=str(tmp_path / "artifacts")),
        )
    )

    assert "artifact_root_dir" in dto.storage_policy
    assert "checksums_computed" in dto.checksum_policy


def test_verifies_readiness_belongs_to_run(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run_a, bundle_a, _, readiness_a, env_spec_a = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    bundle_b, files_b = _completed_bundle(tmp_path / "other")
    bundle_run_repo.add(bundle_b)
    bundle_file_repo.add_many(files_b)
    run_b = _planned_run(bundle_b)
    run_repo.add(run_b)

    with pytest.raises(DetectionTrainingArtifactPolicyNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingArtifactPolicyRequest(
                detection_training_run_id=run_b.id,
                readiness_report_id=readiness_a.id,
                environment_spec_id=env_spec_a.id,
            )
        )


def test_verifies_environment_spec_belongs_to_run(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run_a, bundle_a, _, readiness_a, env_spec_a = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    bundle_b, files_b = _completed_bundle(tmp_path / "other")
    bundle_run_repo.add(bundle_b)
    bundle_file_repo.add_many(files_b)
    run_b = _planned_run(bundle_b)
    run_repo.add(run_b)
    readiness_b = _readiness_report(run_b, bundle_b)
    readiness_report_repo.add(readiness_b)

    with pytest.raises(DetectionTrainingArtifactPolicyNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingArtifactPolicyRequest(
                detection_training_run_id=run_b.id,
                readiness_report_id=readiness_b.id,
                environment_spec_id=env_spec_a.id,
            )
        )


def test_verifies_environment_spec_belongs_to_readiness_report(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    other_readiness = _readiness_report(run, bundle)
    readiness_report_repo.add(other_readiness)

    with pytest.raises(DetectionTrainingArtifactPolicyNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingArtifactPolicyRequest(
                detection_training_run_id=run.id,
                readiness_report_id=other_readiness.id,
                environment_spec_id=env_spec.id,
            )
        )


def test_does_not_modify_detection_training_run(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    original_status = run.status

    use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
        )
    )

    assert run_repo.get_by_id(run.id).status == original_status


def test_does_not_modify_readiness_report(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    original_status = readiness.status

    use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
        )
    )

    assert readiness_report_repo.get_by_id(readiness.id).status == original_status


def test_does_not_modify_environment_spec(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    original_status = env_spec.status

    use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
        )
    )

    assert environment_spec_repo.get_by_id(env_spec.id).status == original_status


def test_rollback_if_record_persistence_fails(tmp_path):
    delegate = InMemoryDetectionTrainingArtifactRecordRepository()
    failing_repo = FailingAddDetectionTrainingArtifactRecordRepository(delegate)
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        _,
        _,
    ) = _build_use_case(record_repository=failing_repo)
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            CreateDetectionTrainingArtifactPolicyRequest(
                detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
            )
        )

    assert policy_repo.list_all() == []


def test_rollback_if_issue_persistence_fails(tmp_path):
    delegate = InMemoryDetectionTrainingArtifactIssueRepository()
    failing_repo = FailingAddDetectionTrainingArtifactIssueRepository(delegate)
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        _,
        _,
    ) = _build_use_case(issue_repository=failing_repo)
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            CreateDetectionTrainingArtifactPolicyRequest(
                detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
            )
        )

    assert policy_repo.list_all() == []


def test_raises_not_found_for_missing_detection_training_run(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    with pytest.raises(DetectionTrainingRunNotFoundError):
        use_case.execute(
            CreateDetectionTrainingArtifactPolicyRequest(
                detection_training_run_id=uuid4(), readiness_report_id=readiness.id, environment_spec_id=env_spec.id
            )
        )


def test_raises_not_found_for_missing_readiness_report(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    with pytest.raises(DetectionTrainingReadinessReportNotFoundError):
        use_case.execute(
            CreateDetectionTrainingArtifactPolicyRequest(
                detection_training_run_id=run.id, readiness_report_id=uuid4(), environment_spec_id=env_spec.id
            )
        )


def test_raises_not_found_for_missing_environment_spec(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        _,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )

    with pytest.raises(DetectionTrainingEnvironmentSpecNotFoundError):
        use_case.execute(
            CreateDetectionTrainingArtifactPolicyRequest(
                detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=uuid4()
            )
        )


def test_lists_policies_by_detection_training_run(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
        )
    )

    assert len(policy_repo.list_by_detection_training_run_id(run.id)) == 1


def test_lists_policies_by_readiness_report(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
        )
    )

    assert len(policy_repo.list_by_readiness_report_id(readiness.id)) == 1


def test_lists_policies_by_environment_spec(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
        )
    )

    assert len(policy_repo.list_by_environment_spec_id(env_spec.id)) == 1


def test_lists_policies_by_annotation_bundle_run(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
        )
    )

    assert len(policy_repo.list_by_annotation_bundle_run_id(run.annotation_bundle_run_id)) == 1


def test_lists_policies_by_dataset_release(tmp_path):
    (
        use_case,
        run_repo,
        readiness_report_repo,
        environment_spec_repo,
        bundle_run_repo,
        bundle_file_repo,
        policy_repo,
        _,
        _,
    ) = _build_use_case()
    run, bundle, _, readiness, env_spec = _seed(
        tmp_path, run_repo, readiness_report_repo, environment_spec_repo, bundle_run_repo, bundle_file_repo
    )
    use_case.execute(
        CreateDetectionTrainingArtifactPolicyRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id, environment_spec_id=env_spec.id
        )
    )

    assert len(policy_repo.list_by_dataset_release_id(run.dataset_release_id)) == 1
