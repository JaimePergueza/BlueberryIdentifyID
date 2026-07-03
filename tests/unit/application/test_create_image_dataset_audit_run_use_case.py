from __future__ import annotations

import copy
import os
from uuid import uuid4

import pytest
from PIL import Image

from blueberry_microid.application.dto.image_audit_dto import CreateImageDatasetAuditRunRequest
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.application.use_cases.image_audit.create_image_dataset_audit_run import (
    CreateImageDatasetAuditRunUseCase,
)
from blueberry_microid.application.use_cases.image_audit.list_image_dataset_audit_runs import (
    ListImageDatasetAuditRunsUseCase,
)
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_dataset_audit_issue_severity import ImageDatasetAuditIssueSeverity
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from blueberry_microid.ml.configs.image_audit_config import ImageAuditConfig
from blueberry_microid.ml.validation.image_dataset_auditor import ImageDatasetAuditor
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetItemRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryDatasetSplitItemRepository,
    InMemoryImageDatasetAuditIssueRepository,
    InMemoryImageDatasetAuditRunRepository,
    InMemoryMicroImageRepository,
    InMemoryPetriImageRepository,
    InMemoryPredictionRepository,
    InMemorySampleRepository,
)


class _StaticManifestExporter:
    def __init__(self, manifest: dict) -> None:
        self.manifest = manifest

    def export(self, _dataset_release_id):
        return copy.deepcopy(self.manifest)


class _FailingImageDatasetAuditIssueRepository(InMemoryImageDatasetAuditIssueRepository):
    def add_many(self, issues):
        super().add_many(issues)
        raise RuntimeError("simulated image audit issue persistence failure")


def _write_valid_image(path, *, width=100, height=100, fmt="JPEG", color="blue"):
    Image.new("RGB", (width, height), color=color).save(str(path), format=fmt)
    return os.path.getsize(str(path))


def _item_dict(index, tmp_path, *, petri_width=100, petri_height=100, petri_path=None, **overrides):
    petri_path = petri_path or str(tmp_path / f"petri-{index}.jpg")
    micro_path = str(tmp_path / f"micro-{index}.png")
    if petri_path and not os.path.exists(petri_path) and overrides.get("_skip_petri_write") is not True:
        _write_valid_image(petri_path, width=petri_width, height=petri_height, fmt="JPEG")
    if not os.path.exists(micro_path):
        _write_valid_image(micro_path, fmt="PNG")
    overrides.pop("_skip_petri_write", None)

    data = {
        "split": "test",
        "analysis_run_id": str(uuid4()),
        "sample_id": str(uuid4()),
        "sample_code": f"S-{index}",
        "lot_code": f"L-{index}",
        "origin": "farm-a",
        "dataset_item_id": str(uuid4()),
        "dataset_split_item_id": str(uuid4()),
        "petri_image_path": petri_path,
        "micro_image_path": micro_path,
        "petri_width": petri_width,
        "petri_height": petri_height,
        "petri_file_size_bytes": os.path.getsize(petri_path) if os.path.exists(petri_path) else None,
        "micro_width": 100,
        "micro_height": 100,
        "micro_file_size_bytes": os.path.getsize(micro_path),
        "ground_truth_label": "suspicious_growth",
        "source_review_decision": "confirmed",
        "prediction_label": "suspicious_growth",
        "final_review_id": str(uuid4()),
    }
    data.update(overrides)
    return data


def _manifest_dict(tmp_path, items=None, release_id=None) -> dict:
    release_id = release_id or uuid4()
    items = items if items is not None else [_item_dict(1, tmp_path)]
    return {
        "dataset_release_id": str(release_id),
        "dataset_snapshot_id": str(uuid4()),
        "name": "release",
        "version": "0.1.0",
        "split_strategy": "by_sample",
        "random_seed": 42,
        "ratios": {"train": 0.7, "validation": 0.15, "test": 0.15},
        "counts": {"total": len(items), "train": 0, "validation": 0, "test": len(items)},
        "label_distribution": {},
        "split_distribution": {},
        "items": items,
    }


def _use_case(manifest: dict, *, issue_repo=None, run_repo=None, config=None):
    run_repo = run_repo or InMemoryImageDatasetAuditRunRepository()
    issue_repo = issue_repo or InMemoryImageDatasetAuditIssueRepository()
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        image_dataset_audit_run_repository=run_repo,
        image_dataset_audit_issue_repository=issue_repo,
    )
    use_case = CreateImageDatasetAuditRunUseCase(
        _StaticManifestExporter(manifest),
        ImageDatasetAuditor(),
        uow,
    )
    return use_case, run_repo, issue_repo, uow


def test_creates_passed_audit_run(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    use_case, _, _, _ = _use_case(manifest)

    dto = use_case.execute(CreateImageDatasetAuditRunRequest(release_id))

    assert dto.status == ImageDatasetAuditStatus.PASSED
    assert dto.is_passed is True
    assert dto.error_count == 0
    assert dto.warning_count == 0
    assert dto.issues == []


def test_creates_warning_audit_run(tmp_path):
    release_id = uuid4()
    item = _item_dict(1, tmp_path, petri_width=10, petri_height=10)
    manifest = _manifest_dict(tmp_path, items=[item], release_id=release_id)
    use_case, _, _, _ = _use_case(manifest)

    dto = use_case.execute(CreateImageDatasetAuditRunRequest(release_id))

    assert dto.status == ImageDatasetAuditStatus.WARNING
    assert dto.is_passed is True
    assert dto.warning_count >= 1
    assert dto.error_count == 0
    assert any(issue.severity == ImageDatasetAuditIssueSeverity.WARNING for issue in dto.issues)


def test_creates_failed_audit_run(tmp_path):
    release_id = uuid4()
    item = _item_dict(2, tmp_path, petri_path=str(tmp_path / "missing.jpg"), _skip_petri_write=True)
    manifest = _manifest_dict(tmp_path, items=[item], release_id=release_id)
    use_case, _, _, _ = _use_case(manifest)

    dto = use_case.execute(CreateImageDatasetAuditRunRequest(release_id))

    assert dto.status == ImageDatasetAuditStatus.FAILED
    assert dto.is_passed is False
    assert dto.error_count >= 1
    assert any(issue.severity == ImageDatasetAuditIssueSeverity.ERROR for issue in dto.issues)


def test_persists_error_and_warning_issues(tmp_path):
    release_id = uuid4()
    missing_item = _item_dict(1, tmp_path, petri_path=str(tmp_path / "missing.jpg"), _skip_petri_write=True)
    small_item = _item_dict(2, tmp_path, petri_width=10, petri_height=10)
    manifest = _manifest_dict(tmp_path, items=[missing_item, small_item], release_id=release_id)
    use_case, run_repo, issue_repo, _ = _use_case(manifest)

    dto = use_case.execute(CreateImageDatasetAuditRunRequest(release_id))

    persisted_issues = issue_repo.list_by_audit_run_id(dto.id)
    assert any(issue.severity == ImageDatasetAuditIssueSeverity.ERROR for issue in persisted_issues)
    assert any(issue.severity == ImageDatasetAuditIssueSeverity.WARNING for issue in persisted_issues)


def test_persists_summary_and_distributions(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    use_case, run_repo, _, _ = _use_case(manifest)

    dto = use_case.execute(CreateImageDatasetAuditRunRequest(release_id))
    persisted = run_repo.get_by_id(dto.id)

    assert persisted.summary["error_count"] == 0
    assert persisted.summary["contains_model_metrics"] is False
    assert persisted.summary["contains_taxonomy"] is False
    assert persisted.format_distribution.get("JPEG") == 1
    assert persisted.format_distribution.get("PNG") == 1
    assert persisted.color_mode_distribution.get("RGB") == 2
    assert sum(persisted.dimension_distribution.values()) == 2
    assert sum(persisted.file_size_distribution.values()) == 2


def test_does_not_modify_dataset_release(tmp_path):
    release_repo = InMemoryDatasetReleaseRepository()
    split_repo = InMemoryDatasetSplitItemRepository()
    item_repo = InMemoryDatasetItemRepository()
    sample_repo = InMemorySampleRepository()
    petri_repo = InMemoryPetriImageRepository()
    micro_repo = InMemoryMicroImageRepository()
    prediction_repo = InMemoryPredictionRepository()
    release, _dataset_item = _seed_release_graph(
        tmp_path, release_repo, split_repo, item_repo, sample_repo, petri_repo, micro_repo, prediction_repo
    )
    release_before = copy.deepcopy(release)

    use_case, _, _, _ = _build_real_exporter_use_case(
        release_repo, split_repo, item_repo, sample_repo, petri_repo, micro_repo, prediction_repo
    )
    use_case.execute(CreateImageDatasetAuditRunRequest(release.id))

    assert release_repo.get_by_id(release.id) == release_before


def test_does_not_modify_dataset_item(tmp_path):
    release_repo = InMemoryDatasetReleaseRepository()
    split_repo = InMemoryDatasetSplitItemRepository()
    item_repo = InMemoryDatasetItemRepository()
    sample_repo = InMemorySampleRepository()
    petri_repo = InMemoryPetriImageRepository()
    micro_repo = InMemoryMicroImageRepository()
    prediction_repo = InMemoryPredictionRepository()
    release, dataset_item = _seed_release_graph(
        tmp_path, release_repo, split_repo, item_repo, sample_repo, petri_repo, micro_repo, prediction_repo
    )
    item_before = copy.deepcopy(dataset_item)

    use_case, _, _, _ = _build_real_exporter_use_case(
        release_repo, split_repo, item_repo, sample_repo, petri_repo, micro_repo, prediction_repo
    )
    use_case.execute(CreateImageDatasetAuditRunRequest(release.id))

    assert item_repo.list_by_dataset_snapshot_id(release.dataset_snapshot_id)[0] == item_before


def test_issue_persistence_failure_rolls_back_audit_run(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id, items=[_item_dict(1, tmp_path, petri_width=10, petri_height=10)])
    run_repo = InMemoryImageDatasetAuditRunRepository()
    issue_repo = _FailingImageDatasetAuditIssueRepository()
    use_case, _, _, _ = _use_case(manifest, run_repo=run_repo, issue_repo=issue_repo)

    with pytest.raises(RuntimeError):
        use_case.execute(CreateImageDatasetAuditRunRequest(release_id))

    assert run_repo.list_all() == []
    assert issue_repo._by_id == {}


def test_config_is_applied_correctly(tmp_path):
    release_id = uuid4()
    item = _item_dict(1, tmp_path, petri_width=10, petri_height=10)
    manifest = _manifest_dict(tmp_path, items=[item], release_id=release_id)
    use_case, _, _, _ = _use_case(manifest)

    lenient_config = ImageAuditConfig(min_width=1, min_height=1)
    dto = use_case.execute(CreateImageDatasetAuditRunRequest(release_id, image_audit_config=lenient_config))

    assert dto.status == ImageDatasetAuditStatus.PASSED
    assert dto.warning_count == 0


def test_lists_audit_runs_by_dataset_release(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    run_repo = InMemoryImageDatasetAuditRunRepository()
    use_case, _, _, _ = _use_case(manifest, run_repo=run_repo)
    use_case.execute(CreateImageDatasetAuditRunRequest(release_id))

    list_use_case = ListImageDatasetAuditRunsUseCase(run_repo)
    results = list_use_case.execute(dataset_release_id=release_id)

    assert len(results) == 1
    assert results[0].dataset_release_id == release_id


def _seed_release_graph(tmp_path, release_repo, split_repo, item_repo, sample_repo, petri_repo, micro_repo, prediction_repo):
    snapshot_id = uuid4()
    sample = sample_repo.add(Sample(sample_code="S-IMGAUDIT", lot_code="L-1", origin="farm-a"))
    petri_path = tmp_path / "petri.jpg"
    micro_path = tmp_path / "micro.png"
    petri_size = _write_valid_image(petri_path, fmt="JPEG")
    micro_size = _write_valid_image(micro_path, fmt="PNG")
    petri = petri_repo.add(
        PetriImage(
            sample_id=sample.id,
            file_path=str(petri_path),
            file_name="petri.jpg",
            mime_type="image/jpeg",
            file_size_bytes=petri_size,
            width=100,
            height=100,
        )
    )
    micro = micro_repo.add(
        MicroImage(
            sample_id=sample.id,
            file_path=str(micro_path),
            file_name="micro.png",
            mime_type="image/png",
            file_size_bytes=micro_size,
            width=100,
            height=100,
        )
    )
    analysis_run_id = uuid4()
    prediction = prediction_repo.add(
        Prediction(analysis_run_id=analysis_run_id, predicted_label=PredictedLabel.SUSPICIOUS_GROWTH)
    )
    dataset_item = DatasetItem(
        dataset_snapshot_id=snapshot_id,
        analysis_run_id=analysis_run_id,
        sample_id=sample.id,
        petri_image_id=petri.id,
        micro_image_id=micro.id,
        prediction_id=prediction.id,
        final_review_id=uuid4(),
        source_review_decision=ReviewDecision.CONFIRMED,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
    )
    item_repo.add_many([dataset_item])
    release = release_repo.add(
        DatasetRelease(
            dataset_snapshot_id=snapshot_id,
            name="release",
            version="0.1.0",
            split_strategy=SplitStrategy.BY_SAMPLE,
            random_seed=42,
            train_ratio=0.7,
            validation_ratio=0.15,
            test_ratio=0.15,
            item_count=1,
            test_count=1,
            label_distribution={"suspicious_growth": 1},
            split_distribution={"test": {"suspicious_growth": 1}},
        )
    )
    split_repo.add_many(
        [
            DatasetSplitItem(
                dataset_release_id=release.id,
                dataset_item_id=dataset_item.id,
                sample_id=sample.id,
                split=DatasetSplit.TEST,
                ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
            )
        ]
    )
    return release, dataset_item


def _build_real_exporter_use_case(release_repo, split_repo, item_repo, sample_repo, petri_repo, micro_repo, prediction_repo):
    run_repo = InMemoryImageDatasetAuditRunRepository()
    issue_repo = InMemoryImageDatasetAuditIssueRepository()
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        image_dataset_audit_run_repository=run_repo,
        image_dataset_audit_issue_repository=issue_repo,
    )
    exporter = DatasetReleaseManifestExporter(
        release_repo, split_repo, item_repo, sample_repo, petri_repo, micro_repo, prediction_repo
    )
    use_case = CreateImageDatasetAuditRunUseCase(exporter, ImageDatasetAuditor(), uow)
    return use_case, run_repo, issue_repo, uow
