import json

import pytest

from blueberry_microid.application.dto.annotation_quality_gate_dto import (
    AnnotationQualityGateConfigDTO,
    CreateAnnotationQualityGateRunRequest,
)
from blueberry_microid.application.services.annotation_quality_gate_validator import AnnotationQualityGateValidator
from blueberry_microid.application.use_cases.annotation_quality_gate.create_annotation_quality_gate_run import (
    CreateAnnotationQualityGateRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.list_annotation_quality_gate_issues import (
    ListAnnotationQualityGateIssuesUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.list_annotation_quality_gate_runs import (
    ListAnnotationQualityGateRunsUseCase,
)
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnnotationBundleFileRepository,
    InMemoryAnnotationBundleRunRepository,
    InMemoryAnnotationQualityGateIssueRepository,
    InMemoryAnnotationQualityGateRunRepository,
)
from tests.unit.application.test_annotation_quality_gate_validator import _completed_bundle


class FailingAnnotationQualityGateIssueRepository(InMemoryAnnotationQualityGateIssueRepository):
    def add_many(self, issues):
        raise RuntimeError("simulated quality gate issue insert failure")


def _build(tmp_path, *, issue_repo=None):
    bundle, files = _completed_bundle(tmp_path)
    bundle_repo = InMemoryAnnotationBundleRunRepository()
    file_repo = InMemoryAnnotationBundleFileRepository()
    gate_repo = InMemoryAnnotationQualityGateRunRepository()
    gate_issue_repo = issue_repo or InMemoryAnnotationQualityGateIssueRepository()
    bundle_repo.add(bundle)
    file_repo.add_many(files)
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        annotation_quality_gate_run_repository=gate_repo,
        annotation_quality_gate_issue_repository=gate_issue_repo,
    )
    use_case = CreateAnnotationQualityGateRunUseCase(
        bundle_repo,
        file_repo,
        AnnotationQualityGateValidator(),
        uow,
    )
    return use_case, bundle, files, gate_repo, gate_issue_repo


def _pass_config(**overrides):
    values = {
        "fail_on_empty_split": False,
        "warn_on_single_class": False,
    }
    values.update(overrides)
    return AnnotationQualityGateConfigDTO(**values)


def test_creates_quality_gate_passed(tmp_path):
    use_case, bundle, _, gate_repo, issue_repo = _build(tmp_path)

    result = use_case.execute(CreateAnnotationQualityGateRunRequest(bundle.id, config=_pass_config()))

    assert result.status.value == "passed"
    assert result.is_passed is True
    assert result.error_count == 0
    assert result.warning_count == 0
    assert gate_repo.get_by_id(result.id) is not None
    assert issue_repo.list_by_quality_gate_run_id(result.id) == []


def test_creates_quality_gate_warning_and_persists_issues(tmp_path):
    use_case, bundle, _, _, issue_repo = _build(tmp_path)

    result = use_case.execute(
        CreateAnnotationQualityGateRunRequest(bundle.id, config=_pass_config(warn_on_single_class=True))
    )

    assert result.status.value == "warning"
    assert result.warning_count == 1
    issues = issue_repo.list_by_quality_gate_run_id(result.id)
    assert issues[0].code == "single_class_only"


def test_creates_quality_gate_failed(tmp_path):
    use_case, bundle, files, _, issue_repo = _build(tmp_path)
    coco_file = next(file for file in files if file.file_role == AnnotationBundleFileRole.COCO_ANNOTATIONS)
    coco_path = tmp_path / "bundle" / coco_file.relative_path
    coco = json.loads(coco_path.read_text(encoding="utf-8"))
    coco["annotations"][0]["image_id"] = "missing"
    coco_path.write_text(json.dumps(coco), encoding="utf-8")

    result = use_case.execute(CreateAnnotationQualityGateRunRequest(bundle.id, config=_pass_config()))

    assert result.status.value == "failed"
    assert result.error_count >= 1
    assert any(issue.code == "manifest_inconsistent" for issue in issue_repo.list_by_quality_gate_run_id(result.id))


def test_does_not_modify_bundle_or_files(tmp_path):
    use_case, bundle, files, *_ = _build(tmp_path)
    before_bundle = bundle.__dict__.copy()
    before_files = [file.__dict__.copy() for file in files]

    use_case.execute(CreateAnnotationQualityGateRunRequest(bundle.id, config=_pass_config()))

    assert bundle.__dict__ == before_bundle
    assert [file.__dict__ for file in files] == before_files


def test_rolls_back_when_issue_persistence_fails(tmp_path):
    failing_issue_repo = FailingAnnotationQualityGateIssueRepository()
    use_case, bundle, _, gate_repo, _ = _build(tmp_path, issue_repo=failing_issue_repo)

    with pytest.raises(RuntimeError, match="simulated quality gate issue insert failure"):
        use_case.execute(
            CreateAnnotationQualityGateRunRequest(bundle.id, config=_pass_config(warn_on_single_class=True))
        )

    assert gate_repo.list_all() == []


def test_lists_quality_gates_by_release_and_bundle(tmp_path):
    use_case, bundle, _, gate_repo, issue_repo = _build(tmp_path)
    result = use_case.execute(CreateAnnotationQualityGateRunRequest(bundle.id, config=_pass_config()))
    list_runs = ListAnnotationQualityGateRunsUseCase(gate_repo)
    list_issues = ListAnnotationQualityGateIssuesUseCase(gate_repo, issue_repo)

    assert [run.id for run in list_runs.execute(dataset_release_id=bundle.dataset_release_id)] == [result.id]
    assert [run.id for run in list_runs.execute(annotation_bundle_run_id=bundle.id)] == [result.id]
    assert list_issues.execute(result.id) == []
