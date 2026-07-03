from uuid import uuid4

import pytest

from blueberry_microid.application.dto.detection_training_readiness_dto import (
    CreateDetectionTrainingReadinessReportRequest,
    DetectionTrainingReadinessConfigDTO,
)
from blueberry_microid.application.exceptions import DetectionTrainingRunNotFoundError
from blueberry_microid.application.services.detection_training_readiness_evaluator import (
    DetectionTrainingReadinessEvaluator,
)
from blueberry_microid.application.use_cases.detection_training_readiness.create_detection_training_readiness_report import (
    CreateDetectionTrainingReadinessReportUseCase,
)
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus
from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle
from tests.unit.application.fakes import (
    FailingAddDetectionTrainingReadinessIssueRepository,
    FakeUnitOfWork,
    InMemoryAnnotationBundleFileRepository,
    InMemoryAnnotationBundleRunRepository,
    InMemoryAnnotationQualityGateIssueRepository,
    InMemoryAnnotationQualityGateRunRepository,
    InMemoryDetectionTrainingIssueRepository,
    InMemoryDetectionTrainingReadinessIssueRepository,
    InMemoryDetectionTrainingReadinessReportRepository,
    InMemoryDetectionTrainingRunRepository,
)


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


def _build_use_case(*, readiness_issue_repository=None):
    bundle_run_repo = InMemoryAnnotationBundleRunRepository()
    bundle_file_repo = InMemoryAnnotationBundleFileRepository()
    quality_gate_run_repo = InMemoryAnnotationQualityGateRunRepository()
    quality_gate_issue_repo = InMemoryAnnotationQualityGateIssueRepository()
    run_repo = InMemoryDetectionTrainingRunRepository()
    issue_repo = InMemoryDetectionTrainingIssueRepository()
    report_repo = InMemoryDetectionTrainingReadinessReportRepository()
    readiness_issue_repo = readiness_issue_repository or InMemoryDetectionTrainingReadinessIssueRepository()
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        detection_training_readiness_report_repository=report_repo,
        detection_training_readiness_issue_repository=readiness_issue_repo,
    )
    use_case = CreateDetectionTrainingReadinessReportUseCase(
        run_repo,
        issue_repo,
        bundle_run_repo,
        bundle_file_repo,
        quality_gate_run_repo,
        quality_gate_issue_repo,
        DetectionTrainingReadinessEvaluator(),
        uow,
    )
    return use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, report_repo, readiness_issue_repo


def _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, **gate_overrides):
    bundle, files = _completed_bundle(tmp_path)
    bundle_run_repo.add(bundle)
    bundle_file_repo.add_many(files)
    gate = _quality_gate(bundle, **gate_overrides)
    quality_gate_run_repo.add(gate)
    run = _planned_run(bundle, gate)
    run_repo.add(run)
    return run, bundle, files, gate


def test_creates_ready_report(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, report_repo, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)

    dto = use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    assert dto.decision == DetectionTrainingReadinessDecision.READY_FOR_TRAINING
    assert dto.is_ready is True
    assert report_repo.get_by_id(dto.id) is not None


def test_creates_needs_more_annotations_report(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, _, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, total_images=1)

    dto = use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    assert dto.decision == DetectionTrainingReadinessDecision.NEEDS_MORE_ANNOTATIONS
    assert dto.status == DetectionTrainingReadinessStatus.BLOCKED
    assert dto.is_ready is False


def test_creates_blocked_by_quality_report(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, _, _ = _build_use_case()
    run, *_ = _seed(
        tmp_path,
        run_repo,
        bundle_run_repo,
        bundle_file_repo,
        quality_gate_run_repo,
        status=AnnotationQualityGateStatus.FAILED,
        error_count=1,
    )

    dto = use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    assert dto.decision == DetectionTrainingReadinessDecision.BLOCKED_BY_QUALITY


def test_creates_blocked_by_environment_report(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, _, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)
    request = CreateDetectionTrainingReadinessReportRequest(
        detection_training_run_id=run.id,
        config=DetectionTrainingReadinessConfigDTO(require_gpu=True),
    )

    dto = use_case.execute(request)

    assert dto.decision == DetectionTrainingReadinessDecision.BLOCKED_BY_ENVIRONMENT


def test_persists_issues(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, _, readiness_issue_repo = (
        _build_use_case()
    )
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)

    dto = use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    issues = readiness_issue_repo.list_by_readiness_report_id(dto.id)
    assert len(issues) > 0
    assert all(issue.readiness_report_id == dto.id for issue in issues)


def test_persists_summaries(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, _, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)

    dto = use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    assert dto.data_summary["total_images"] == 10
    assert dto.quality_summary["quality_gate_is_passed"] is True


def test_does_not_modify_detection_training_run(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, _, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)
    original_status = run.status

    use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    persisted_run = run_repo.get_by_id(run.id)
    assert persisted_run.status == original_status


def test_does_not_modify_annotation_bundle_run(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, _, _ = _build_use_case()
    run, bundle, _, _ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)
    original_status = bundle.status

    use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    persisted_bundle = bundle_run_repo.get_by_id(bundle.id)
    assert persisted_bundle.status == original_status


def test_does_not_modify_annotation_quality_gate_run(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, _, _ = _build_use_case()
    run, _, _, gate = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)
    original_status = gate.status

    use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    persisted_gate = quality_gate_run_repo.get_by_id(gate.id)
    assert persisted_gate.status == original_status


def test_rollback_if_issue_persistence_fails(tmp_path):
    delegate = InMemoryDetectionTrainingReadinessIssueRepository()
    failing_repo = FailingAddDetectionTrainingReadinessIssueRepository(delegate)
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, report_repo, _ = _build_use_case(
        readiness_issue_repository=failing_repo
    )
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)

    with pytest.raises(RuntimeError):
        use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    assert report_repo.list_all() == []


def test_raises_not_found_for_missing_detection_training_run():
    use_case, *_ = _build_use_case()

    with pytest.raises(DetectionTrainingRunNotFoundError):
        use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=uuid4()))


def test_lists_reports_by_detection_training_run(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, report_repo, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)
    use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    reports = report_repo.list_by_detection_training_run_id(run.id)

    assert len(reports) == 1


def test_lists_reports_by_dataset_release(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, report_repo, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)
    use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    reports = report_repo.list_by_dataset_release_id(run.dataset_release_id)

    assert len(reports) == 1


def test_lists_reports_by_annotation_bundle_run(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, report_repo, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)
    use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    reports = report_repo.list_by_annotation_bundle_run_id(run.annotation_bundle_run_id)

    assert len(reports) == 1


def test_lists_reports_by_annotation_quality_gate_run(tmp_path):
    use_case, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo, report_repo, _ = _build_use_case()
    run, *_ = _seed(tmp_path, run_repo, bundle_run_repo, bundle_file_repo, quality_gate_run_repo)
    use_case.execute(CreateDetectionTrainingReadinessReportRequest(detection_training_run_id=run.id))

    reports = report_repo.list_by_annotation_quality_gate_run_id(run.annotation_quality_gate_run_id)

    assert len(reports) == 1
