from uuid import uuid4

import pytest

from blueberry_microid.application.dto.detection_training_environment_dto import (
    CreateDetectionTrainingEnvironmentSpecRequest,
    DetectionTrainingEnvironmentConfigDTO,
)
from blueberry_microid.application.exceptions import (
    DetectionTrainingEnvironmentNotAllowedError,
    DetectionTrainingReadinessReportNotFoundError,
    DetectionTrainingRunNotFoundError,
)
from blueberry_microid.application.services.detection_training_environment_evaluator import (
    DetectionTrainingEnvironmentEvaluator,
)
from blueberry_microid.application.use_cases.detection_training_environment.create_detection_training_environment_spec import (
    CreateDetectionTrainingEnvironmentSpecUseCase,
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
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle
from tests.unit.application.fakes import (
    FailingAddDetectionTrainingEnvironmentIssueRepository,
    FakeUnitOfWork,
    InMemoryAnnotationBundleFileRepository,
    InMemoryAnnotationBundleRunRepository,
    InMemoryDetectionTrainingEnvironmentIssueRepository,
    InMemoryDetectionTrainingEnvironmentSpecRepository,
    InMemoryDetectionTrainingReadinessReportRepository,
    InMemoryDetectionTrainingRunRepository,
)


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


def _build_use_case(*, environment_issue_repository=None):
    bundle_run_repo = InMemoryAnnotationBundleRunRepository()
    bundle_file_repo = InMemoryAnnotationBundleFileRepository()
    run_repo = InMemoryDetectionTrainingRunRepository()
    readiness_report_repo = InMemoryDetectionTrainingReadinessReportRepository()
    spec_repo = InMemoryDetectionTrainingEnvironmentSpecRepository()
    issue_repo = environment_issue_repository or InMemoryDetectionTrainingEnvironmentIssueRepository()
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        detection_training_environment_spec_repository=spec_repo,
        detection_training_environment_issue_repository=issue_repo,
    )
    use_case = CreateDetectionTrainingEnvironmentSpecUseCase(
        run_repo,
        readiness_report_repo,
        bundle_run_repo,
        bundle_file_repo,
        DetectionTrainingEnvironmentEvaluator(),
        uow,
    )
    return use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, spec_repo, issue_repo


def _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, **readiness_overrides):
    bundle, files = _completed_bundle(tmp_path)
    bundle_run_repo.add(bundle)
    bundle_file_repo.add_many(files)
    run = _planned_run(bundle)
    run_repo.add(run)
    readiness = _readiness_report(run, bundle, **readiness_overrides)
    readiness_report_repo.add(readiness)
    return run, bundle, files, readiness


def _config_dto(**overrides):
    return DetectionTrainingEnvironmentConfigDTO(**overrides)


def test_creates_ready_spec(tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, spec_repo, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)

    dto = use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id,
            readiness_report_id=readiness.id,
            config=_config_dto(
                allow_cpu_training=False,
                artifact_output_dir=str(tmp_path),
                pretrained_weights_policy="not_applicable",
            ),
        )
    )

    assert dto.decision == DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY
    assert dto.is_environment_ready is True
    assert spec_repo.get_by_id(dto.id) is not None


def test_creates_warning_spec(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)

    dto = use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert dto.status == DetectionTrainingEnvironmentStatus.WARNING
    assert dto.decision == DetectionTrainingEnvironmentDecision.NEEDS_MANUAL_SETUP


def test_creates_blocked_spec(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    run, bundle, _, readiness = _seed(
        tmp_path,
        run_repo,
        readiness_report_repo,
        bundle_run_repo,
        bundle_file_repo,
        status=DetectionTrainingReadinessStatus.BLOCKED,
        error_count=1,
        is_ready=False,
    )

    dto = use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert dto.status == DetectionTrainingEnvironmentStatus.BLOCKED
    assert dto.is_environment_ready is False


def test_persists_issues(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, issue_repo = (
        _build_use_case()
    )
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)

    dto = use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    issues = issue_repo.list_by_environment_spec_id(dto.id)
    assert len(issues) > 0
    assert all(issue.environment_spec_id == dto.id for issue in issues)


def test_persists_policies_and_summaries(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)

    dto = use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert "detected_python_version" in dto.detected_environment
    assert "require_ultralytics" in dto.dependency_policy
    assert "require_gpu" in dto.hardware_policy
    assert "artifact_output_dir" in dto.artifact_policy
    assert "allow_ci_training" in dto.execution_policy


def test_verifies_readiness_belongs_to_run(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    run_a, bundle_a, _, readiness_a = _seed(
        tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo
    )
    bundle_b, files_b = _completed_bundle(tmp_path / "other")
    bundle_run_repo.add(bundle_b)
    bundle_file_repo.add_many(files_b)
    run_b = _planned_run(bundle_b)
    run_repo.add(run_b)

    with pytest.raises(DetectionTrainingEnvironmentNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingEnvironmentSpecRequest(
                detection_training_run_id=run_b.id, readiness_report_id=readiness_a.id
            )
        )


def test_does_not_modify_detection_training_run(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)
    original_status = run.status

    use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert run_repo.get_by_id(run.id).status == original_status


def test_does_not_modify_readiness_report(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)
    original_status = readiness.status

    use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert readiness_report_repo.get_by_id(readiness.id).status == original_status


def test_does_not_modify_annotation_bundle_run(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)
    original_status = bundle.status

    use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert bundle_run_repo.get_by_id(bundle.id).status == original_status


def test_rollback_if_issue_persistence_fails(tmp_path):
    delegate = InMemoryDetectionTrainingEnvironmentIssueRepository()
    failing_repo = FailingAddDetectionTrainingEnvironmentIssueRepository(delegate)
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, spec_repo, _ = _build_use_case(
        environment_issue_repository=failing_repo
    )
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)

    with pytest.raises(RuntimeError):
        use_case.execute(
            CreateDetectionTrainingEnvironmentSpecRequest(
                detection_training_run_id=run.id, readiness_report_id=readiness.id
            )
        )

    assert spec_repo.list_all() == []


def test_raises_not_found_for_missing_detection_training_run(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    _, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)

    with pytest.raises(DetectionTrainingRunNotFoundError):
        use_case.execute(
            CreateDetectionTrainingEnvironmentSpecRequest(
                detection_training_run_id=uuid4(), readiness_report_id=readiness.id
            )
        )


def test_raises_not_found_for_missing_readiness_report(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, _, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)

    with pytest.raises(DetectionTrainingReadinessReportNotFoundError):
        use_case.execute(
            CreateDetectionTrainingEnvironmentSpecRequest(
                detection_training_run_id=run.id, readiness_report_id=uuid4()
            )
        )


def test_lists_specs_by_detection_training_run(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, spec_repo, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)
    use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert len(spec_repo.list_by_detection_training_run_id(run.id)) == 1


def test_lists_specs_by_readiness_report(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, spec_repo, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)
    use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert len(spec_repo.list_by_readiness_report_id(readiness.id)) == 1


def test_lists_specs_by_annotation_bundle_run(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, spec_repo, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)
    use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert len(spec_repo.list_by_annotation_bundle_run_id(run.annotation_bundle_run_id)) == 1


def test_lists_specs_by_dataset_release(tmp_path):
    use_case, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo, spec_repo, _ = _build_use_case()
    run, bundle, _, readiness = _seed(tmp_path, run_repo, readiness_report_repo, bundle_run_repo, bundle_file_repo)
    use_case.execute(
        CreateDetectionTrainingEnvironmentSpecRequest(
            detection_training_run_id=run.id, readiness_report_id=readiness.id
        )
    )

    assert len(spec_repo.list_by_dataset_release_id(run.dataset_release_id)) == 1
