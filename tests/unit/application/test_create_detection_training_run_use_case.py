from uuid import uuid4

import pytest

from blueberry_microid.application.dto.detection_training_dto import CreateDetectionTrainingRunRequest
from blueberry_microid.application.exceptions import (
    AnnotationBundleRunNotFoundError,
    AnnotationQualityGateRunNotFoundError,
    DetectionTrainingNotAllowedError,
)
from blueberry_microid.application.use_cases.detection_training.create_detection_training_run import (
    CreateDetectionTrainingRunUseCase,
)
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.training.yolo_dry_run_trainer import YoloDryRunTrainer
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle
from tests.unit.application.fakes import (
    FailingAddDetectionTrainingIssueRepository,
    FakeUnitOfWork,
    InMemoryAnnotationBundleFileRepository,
    InMemoryAnnotationBundleRunRepository,
    InMemoryAnnotationQualityGateRunRepository,
    InMemoryDetectionTrainingIssueRepository,
    InMemoryDetectionTrainingRunRepository,
)


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


def _build_use_case(*, issue_repository=None):
    bundle_run_repo = InMemoryAnnotationBundleRunRepository()
    bundle_file_repo = InMemoryAnnotationBundleFileRepository()
    quality_gate_repo = InMemoryAnnotationQualityGateRunRepository()
    run_repo = InMemoryDetectionTrainingRunRepository()
    issue_repo = issue_repository or InMemoryDetectionTrainingIssueRepository()
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        detection_training_run_repository=run_repo,
        detection_training_issue_repository=issue_repo,
    )
    use_case = CreateDetectionTrainingRunUseCase(
        bundle_run_repo, bundle_file_repo, quality_gate_repo, YoloDryRunTrainer(), uow
    )
    return use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, run_repo, issue_repo


def _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path, **gate_overrides):
    bundle, files = _completed_bundle(tmp_path)
    bundle_run_repo.add(bundle)
    bundle_file_repo.add_many(files)
    gate = _quality_gate(bundle, **gate_overrides)
    quality_gate_repo.add(gate)
    return bundle, files, gate


def test_creates_planned_run(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, _, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)

    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    assert result.status == DetectionTrainingStatus.PLANNED
    assert result.is_runnable is True


def test_creates_informational_issues(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, _, issue_repo = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)

    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    issues = issue_repo.list_by_detection_training_run_id(result.id)
    assert any(issue.code == "no_training_executed" for issue in issues)


def test_creates_blocked_run_when_quality_gate_not_passed(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, _, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(
        bundle_run_repo,
        bundle_file_repo,
        quality_gate_repo,
        tmp_path,
        status=AnnotationQualityGateStatus.FAILED,
        error_count=1,
    )

    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    assert result.status == DetectionTrainingStatus.BLOCKED
    assert result.is_runnable is False


def test_creates_blocked_run_when_yolo_labels_missing(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, _, _ = _build_use_case()
    bundle, files, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)
    for file in list(bundle_file_repo._by_id.values()):
        if file.file_role.value == "yolo_label":
            del bundle_file_repo._by_id[file.id]

    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    assert result.status == DetectionTrainingStatus.BLOCKED


def test_verifies_quality_gate_belongs_to_bundle(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, _, _ = _build_use_case()
    bundle_a, _, gate_a = _seed_bundle_and_gate(
        bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path / "a"
    )
    bundle_b, _, _ = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path / "b")

    with pytest.raises(DetectionTrainingNotAllowedError):
        use_case.execute(
            CreateDetectionTrainingRunRequest(
                annotation_bundle_run_id=bundle_b.id,
                annotation_quality_gate_run_id=gate_a.id,
            )
        )


def test_persists_training_plan(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, run_repo, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)

    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    stored = run_repo.get_by_id(result.id)
    assert stored.training_plan["algorithm"] == "yolo_dry_run"


def test_persists_command_preview(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, run_repo, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)

    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    stored = run_repo.get_by_id(result.id)
    assert stored.command_preview["dry_run_only"] is True


def test_persists_expected_outputs(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, run_repo, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)

    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    stored = run_repo.get_by_id(result.id)
    assert "weights_path_planned" in stored.expected_outputs


def test_does_not_modify_annotation_bundle_run(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, _, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)
    original_status = bundle.status

    use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    stored_bundle = bundle_run_repo.get_by_id(bundle.id)
    assert stored_bundle.status == original_status


def test_does_not_modify_annotation_quality_gate_run(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, _, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)
    original_status = gate.status

    use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    stored_gate = quality_gate_repo.get_by_id(gate.id)
    assert stored_gate.status == original_status


def test_rollback_on_issue_persistence_failure(tmp_path):
    base_issue_repo = InMemoryDetectionTrainingIssueRepository()
    failing_issue_repo = FailingAddDetectionTrainingIssueRepository(base_issue_repo)
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, run_repo, _ = _build_use_case(
        issue_repository=failing_issue_repo
    )
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)

    with pytest.raises(RuntimeError, match="simulated detection training issue insert failure"):
        use_case.execute(
            CreateDetectionTrainingRunRequest(
                annotation_bundle_run_id=bundle.id,
                annotation_quality_gate_run_id=gate.id,
            )
        )

    assert run_repo.list_all() == []


def test_raises_when_bundle_does_not_exist():
    use_case, *_ = _build_use_case()

    with pytest.raises(AnnotationBundleRunNotFoundError):
        use_case.execute(
            CreateDetectionTrainingRunRequest(
                annotation_bundle_run_id=uuid4(),
                annotation_quality_gate_run_id=uuid4(),
            )
        )


def test_raises_when_quality_gate_does_not_exist(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, _, _ = _build_use_case()
    bundle, files = _completed_bundle(tmp_path)
    bundle_run_repo.add(bundle)
    bundle_file_repo.add_many(files)

    with pytest.raises(AnnotationQualityGateRunNotFoundError):
        use_case.execute(
            CreateDetectionTrainingRunRequest(
                annotation_bundle_run_id=bundle.id,
                annotation_quality_gate_run_id=uuid4(),
            )
        )


def test_lists_runs_by_dataset_release(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, run_repo, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)
    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    runs = run_repo.list_by_dataset_release_id(bundle.dataset_release_id)
    assert [run.id for run in runs] == [result.id]


def test_lists_runs_by_annotation_bundle_run(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, run_repo, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)
    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    runs = run_repo.list_by_annotation_bundle_run_id(bundle.id)
    assert [run.id for run in runs] == [result.id]


def test_lists_runs_by_annotation_quality_gate_run(tmp_path):
    use_case, bundle_run_repo, bundle_file_repo, quality_gate_repo, run_repo, _ = _build_use_case()
    bundle, _, gate = _seed_bundle_and_gate(bundle_run_repo, bundle_file_repo, quality_gate_repo, tmp_path)
    result = use_case.execute(
        CreateDetectionTrainingRunRequest(
            annotation_bundle_run_id=bundle.id,
            annotation_quality_gate_run_id=gate.id,
        )
    )

    runs = run_repo.list_by_annotation_quality_gate_run_id(gate.id)
    assert [run.id for run in runs] == [result.id]
