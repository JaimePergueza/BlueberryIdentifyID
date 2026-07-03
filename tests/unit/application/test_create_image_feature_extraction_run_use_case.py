from __future__ import annotations

import copy
import os
from uuid import uuid4

import pytest
from PIL import Image

from blueberry_microid.application.dto.image_feature_extraction_dto import CreateImageFeatureExtractionRunRequest
from blueberry_microid.application.exceptions import ImageFeatureExtractionNotAllowedError
from blueberry_microid.application.use_cases.image_feature_extraction.create_image_feature_extraction_run import (
    CreateImageFeatureExtractionRunUseCase,
)
from blueberry_microid.application.use_cases.image_feature_extraction.list_image_feature_extraction_runs import (
    ListImageFeatureExtractionRunsUseCase,
)
from blueberry_microid.domain.entities.image_dataset_audit_run import ImageDatasetAuditRun
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.ml.configs.image_feature_extraction_config import ImageFeatureExtractionConfig
from blueberry_microid.ml.preprocessing.image_feature_extractor import ImageFeatureExtractor
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryImageDatasetAuditRunRepository,
    InMemoryImageFeatureExtractionRunRepository,
    InMemoryImageFeatureVectorRepository,
    InMemoryPredictionRepository,
)


class _StaticManifestExporter:
    def __init__(self, manifest: dict) -> None:
        self.manifest = manifest

    def export(self, _dataset_release_id):
        return copy.deepcopy(self.manifest)


class _FailingImageFeatureVectorRepository(InMemoryImageFeatureVectorRepository):
    def add_many(self, feature_vectors):
        super().add_many(feature_vectors)
        raise RuntimeError("simulated feature vector persistence failure")


def _write_valid_image(path, *, width=100, height=100, fmt="JPEG", color="blue"):
    Image.new("RGB", (width, height), color=color).save(str(path), format=fmt)
    return os.path.getsize(str(path))


def _item_dict(index, tmp_path, **overrides):
    petri_path = str(tmp_path / f"petri-{index}.jpg")
    micro_path = str(tmp_path / f"micro-{index}.png")
    if not os.path.exists(petri_path):
        _write_valid_image(petri_path, fmt="JPEG")
    if not os.path.exists(micro_path):
        _write_valid_image(micro_path, fmt="PNG")

    data = {
        "split": "test",
        "analysis_run_id": str(uuid4()),
        "sample_id": str(uuid4()),
        "sample_code": f"S-{index}",
        "dataset_item_id": str(uuid4()),
        "dataset_split_item_id": str(uuid4()),
        "petri_image_path": petri_path,
        "micro_image_path": micro_path,
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


def _audit_run(dataset_release_id, *, status=ImageDatasetAuditStatus.PASSED) -> ImageDatasetAuditRun:
    is_passed = status != ImageDatasetAuditStatus.FAILED
    return ImageDatasetAuditRun(
        dataset_release_id=dataset_release_id,
        status=status,
        is_passed=is_passed,
        total_items=1,
        total_petri_images=1,
        total_micro_images=1,
        checked_petri_images=1,
        checked_micro_images=1,
        failed_petri_images=0,
        failed_micro_images=0,
        warning_count=1 if status == ImageDatasetAuditStatus.WARNING else 0,
        error_count=1 if status == ImageDatasetAuditStatus.FAILED else 0,
        summary={},
        format_distribution={},
        color_mode_distribution={},
        dimension_distribution={},
        file_size_distribution={},
    )


def _ensure_release(release_repo, release_id) -> None:
    if release_repo.get_by_id(release_id) is not None:
        return
    from blueberry_microid.domain.entities.dataset_release import DatasetRelease
    from blueberry_microid.domain.enums.split_strategy import SplitStrategy

    release_repo.add(
        DatasetRelease(
            id=release_id,
            dataset_snapshot_id=uuid4(),
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


def _use_case(manifest, audit_run, *, run_repo=None, vector_repo=None, release_repo=None, audit_repo=None):
    release_repo = release_repo or InMemoryDatasetReleaseRepository()
    audit_repo = audit_repo or InMemoryImageDatasetAuditRunRepository()
    run_repo = run_repo or InMemoryImageFeatureExtractionRunRepository()
    vector_repo = vector_repo or InMemoryImageFeatureVectorRepository()
    _ensure_release(release_repo, audit_run.dataset_release_id)
    audit_repo.add(audit_run)
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        image_feature_extraction_run_repository=run_repo,
        image_feature_vector_repository=vector_repo,
    )
    use_case = CreateImageFeatureExtractionRunUseCase(
        release_repo,
        audit_repo,
        _StaticManifestExporter(manifest),
        ImageFeatureExtractor(),
        uow,
    )
    return use_case, run_repo, vector_repo, release_repo, audit_repo, uow


def test_creates_completed_run_with_passed_audit(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.PASSED)
    use_case, _, _, _, _, _ = _use_case(manifest, audit_run)

    dto = use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))

    assert dto.status == ImageFeatureExtractionStatus.COMPLETED
    assert dto.is_completed is True


def test_creates_completed_run_with_warning_audit_when_allowed(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.WARNING)
    use_case, _, _, _, _, _ = _use_case(manifest, audit_run)

    config = ImageFeatureExtractionConfig(allow_audit_warning=True)
    dto = use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id, config))

    assert dto.status == ImageFeatureExtractionStatus.COMPLETED


def test_rejects_warning_audit_when_not_allowed(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.WARNING)
    use_case, _, _, _, _, _ = _use_case(manifest, audit_run)

    config = ImageFeatureExtractionConfig(allow_audit_warning=False)
    with pytest.raises(ImageFeatureExtractionNotAllowedError):
        use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id, config))


def test_rejects_failed_audit(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.FAILED)
    use_case, _, _, _, _, _ = _use_case(manifest, audit_run)

    with pytest.raises(ImageFeatureExtractionNotAllowedError):
        use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))


def test_rejects_audit_not_belonging_to_release(tmp_path):
    release_id = uuid4()
    other_release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(other_release_id, status=ImageDatasetAuditStatus.PASSED)
    use_case, _, _, release_repo, _, _ = _use_case(manifest, audit_run)
    _ensure_release(release_repo, release_id)

    with pytest.raises(ImageFeatureExtractionNotAllowedError):
        use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))


def test_persists_petri_and_micro_vectors(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.PASSED)
    use_case, run_repo, vector_repo, _, _, _ = _use_case(manifest, audit_run)

    dto = use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))

    persisted = vector_repo.list_by_feature_extraction_run_id(dto.id)
    modalities = {v.modality for v in persisted}
    assert modalities == {ImageModality.PETRI, ImageModality.MICRO}


def test_persists_config_and_summary(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.PASSED)
    use_case, run_repo, _, _, _, _ = _use_case(manifest, audit_run)

    config = ImageFeatureExtractionConfig(histogram_bins=8)
    dto = use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id, config))
    persisted = run_repo.get_by_id(dto.id)

    assert persisted.config["histogram_bins"] == 8
    assert persisted.summary["contains_model_metrics"] is False
    assert persisted.summary["contains_taxonomy"] is False


def test_does_not_modify_dataset_release(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.PASSED)
    use_case, _, _, release_repo, _, _ = _use_case(manifest, audit_run)
    release_before = copy.deepcopy(release_repo.get_by_id(release_id))

    use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))

    assert release_repo.get_by_id(release_id) == release_before


def test_does_not_modify_image_dataset_audit_run(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.PASSED)
    use_case, _, _, _, audit_repo, _ = _use_case(manifest, audit_run)
    audit_before = copy.deepcopy(audit_repo.get_by_id(audit_run.id))

    use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))

    assert audit_repo.get_by_id(audit_run.id) == audit_before


def test_vector_persistence_failure_rolls_back_extraction_run(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.PASSED)
    run_repo = InMemoryImageFeatureExtractionRunRepository()
    vector_repo = _FailingImageFeatureVectorRepository()
    use_case, _, _, _, _, _ = _use_case(manifest, audit_run, run_repo=run_repo, vector_repo=vector_repo)

    with pytest.raises(RuntimeError):
        use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))

    assert run_repo.list_all() == []
    assert vector_repo._by_id == {}


def test_lists_extraction_runs_by_dataset_release(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.PASSED)
    run_repo = InMemoryImageFeatureExtractionRunRepository()
    use_case, _, _, release_repo, _, _ = _use_case(manifest, audit_run, run_repo=run_repo)
    use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))

    list_use_case = ListImageFeatureExtractionRunsUseCase(run_repo, release_repo)
    results = list_use_case.execute(dataset_release_id=release_id)

    assert len(results) == 1
    assert results[0].dataset_release_id == release_id


def test_lists_extraction_runs_by_image_audit_run(tmp_path):
    release_id = uuid4()
    manifest = _manifest_dict(tmp_path, release_id=release_id)
    audit_run = _audit_run(release_id, status=ImageDatasetAuditStatus.PASSED)
    run_repo = InMemoryImageFeatureExtractionRunRepository()
    use_case, _, _, _, audit_repo, _ = _use_case(manifest, audit_run, run_repo=run_repo)
    use_case.execute(CreateImageFeatureExtractionRunRequest(release_id, audit_run.id))

    list_use_case = ListImageFeatureExtractionRunsUseCase(run_repo, image_dataset_audit_run_repository=audit_repo)
    results = list_use_case.execute(image_audit_run_id=audit_run.id)

    assert len(results) == 1
    assert results[0].image_audit_run_id == audit_run.id
