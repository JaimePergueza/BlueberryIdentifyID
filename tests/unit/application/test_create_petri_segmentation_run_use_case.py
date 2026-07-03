from __future__ import annotations

import copy
import os
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw

from blueberry_microid.application.dto.petri_segmentation_dto import CreatePetriSegmentationRunRequest
from blueberry_microid.application.exceptions import PetriSegmentationNotAllowedError
from blueberry_microid.application.use_cases.petri_segmentation.create_petri_segmentation_run import (
    CreatePetriSegmentationRunUseCase,
)
from blueberry_microid.application.use_cases.petri_segmentation.list_petri_segmentation_runs import (
    ListPetriSegmentationRunsUseCase,
)
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.image_dataset_audit_run import ImageDatasetAuditRun
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from blueberry_microid.ml.configs.petri_segmentation_config import PetriSegmentationConfig
from blueberry_microid.ml.preprocessing.classical_petri_segmenter import ClassicalPetriSegmenter
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryImageDatasetAuditRunRepository,
    InMemoryPetriSegmentationRegionRepository,
    InMemoryPetriSegmentationRunRepository,
    InMemoryPredictionRepository,
)


class _StaticManifestExporter:
    def __init__(self, manifest: dict) -> None:
        self.manifest = manifest

    def export(self, _dataset_release_id):
        return copy.deepcopy(self.manifest)


class _FailingPetriSegmentationRegionRepository(InMemoryPetriSegmentationRegionRepository):
    def add_many(self, regions):
        super().add_many(regions)
        raise RuntimeError("simulated region persistence failure")


def _write_petri(path):
    image = Image.new("RGB", (120, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((40, 40, 80, 80), fill="black")
    image.save(path, format="PNG")
    return os.path.getsize(path)


def _manifest(tmp_path, release_id):
    petri_path = tmp_path / "petri.png"
    _write_petri(petri_path)
    return {
        "dataset_release_id": str(release_id),
        "dataset_snapshot_id": str(uuid4()),
        "name": "release",
        "version": "0.1.0",
        "split_strategy": "by_sample",
        "random_seed": 42,
        "ratios": {"train": 0.0, "validation": 0.0, "test": 1.0},
        "counts": {"total": 1, "train": 0, "validation": 0, "test": 1},
        "items": [
            {
                "split": "test",
                "analysis_run_id": str(uuid4()),
                "sample_id": str(uuid4()),
                "sample_code": "S-PETRI",
                "dataset_item_id": str(uuid4()),
                "dataset_split_item_id": str(uuid4()),
                "petri_image_path": str(petri_path),
                "micro_image_path": str(tmp_path / "micro-not-used.png"),
                "ground_truth_label": "suspicious_growth",
                "source_review_decision": "confirmed",
                "prediction_label": "suspicious_growth",
                "final_review_id": str(uuid4()),
            }
        ],
    }


def _release(release_id):
    return DatasetRelease(
        id=release_id,
        dataset_snapshot_id=uuid4(),
        name="release",
        version="0.1.0",
        split_strategy=SplitStrategy.BY_SAMPLE,
        random_seed=42,
        train_ratio=0.0,
        validation_ratio=0.0,
        test_ratio=1.0,
        item_count=1,
        test_count=1,
        label_distribution={"suspicious_growth": 1},
        split_distribution={"test": {"suspicious_growth": 1}},
    )


def _audit(release_id, *, status=ImageDatasetAuditStatus.PASSED):
    return ImageDatasetAuditRun(
        dataset_release_id=release_id,
        status=status,
        is_passed=status != ImageDatasetAuditStatus.FAILED,
        total_items=1,
        total_petri_images=1,
        total_micro_images=1,
        checked_petri_images=1,
        checked_micro_images=1,
        failed_petri_images=0 if status != ImageDatasetAuditStatus.FAILED else 1,
        failed_micro_images=0,
        warning_count=0,
        error_count=1 if status == ImageDatasetAuditStatus.FAILED else 0,
        summary={},
        format_distribution={},
        color_mode_distribution={},
        dimension_distribution={},
        file_size_distribution={},
    )


def _use_case(tmp_path, release_id=None, audit_run=None, *, run_repo=None, region_repo=None):
    release_id = release_id or uuid4()
    manifest = _manifest(tmp_path, release_id)
    release_repo = InMemoryDatasetReleaseRepository()
    release_repo.add(_release(release_id))
    audit_repo = InMemoryImageDatasetAuditRunRepository()
    audit_run = audit_run if audit_run is not None else _audit(release_id)
    if audit_run is not None:
        audit_repo.add(audit_run)
    run_repo = run_repo or InMemoryPetriSegmentationRunRepository()
    region_repo = region_repo or InMemoryPetriSegmentationRegionRepository()
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        petri_segmentation_run_repository=run_repo,
        petri_segmentation_region_repository=region_repo,
    )
    use_case = CreatePetriSegmentationRunUseCase(
        release_repo,
        audit_repo,
        _StaticManifestExporter(manifest),
        ClassicalPetriSegmenter(),
        uow,
    )
    return use_case, run_repo, region_repo, release_repo, audit_repo, audit_run


def test_creates_completed_run_with_passed_audit(tmp_path):
    release_id = uuid4()
    use_case, _run_repo, _region_repo, _release_repo, _audit_repo, audit_run = _use_case(tmp_path, release_id)

    dto = use_case.execute(CreatePetriSegmentationRunRequest(release_id, audit_run.id))

    assert dto.status == PetriSegmentationStatus.COMPLETED
    assert dto.total_regions_detected == 1
    assert dto.regions[0].area_px > 1000


def test_creates_completed_run_without_audit(tmp_path):
    release_id = uuid4()
    use_case, _run_repo, _region_repo, _release_repo, _audit_repo, _audit_run = _use_case(tmp_path, release_id)

    dto = use_case.execute(CreatePetriSegmentationRunRequest(release_id))

    assert dto.status == PetriSegmentationStatus.COMPLETED
    assert dto.image_audit_run_id is None


def test_rejects_failed_audit(tmp_path):
    release_id = uuid4()
    failed_audit = _audit(release_id, status=ImageDatasetAuditStatus.FAILED)
    use_case, *_ = _use_case(tmp_path, release_id, audit_run=failed_audit)

    with pytest.raises(PetriSegmentationNotAllowedError):
        use_case.execute(CreatePetriSegmentationRunRequest(release_id, failed_audit.id))


def test_rejects_audit_from_different_release(tmp_path):
    release_id = uuid4()
    other_audit = _audit(uuid4(), status=ImageDatasetAuditStatus.PASSED)
    use_case, *_ = _use_case(tmp_path, release_id, audit_run=other_audit)

    with pytest.raises(PetriSegmentationNotAllowedError):
        use_case.execute(CreatePetriSegmentationRunRequest(release_id, other_audit.id))


def test_persists_regions_config_and_summary(tmp_path):
    release_id = uuid4()
    use_case, run_repo, region_repo, *_rest = _use_case(tmp_path, release_id)

    dto = use_case.execute(
        CreatePetriSegmentationRunRequest(release_id, config=PetriSegmentationConfig(min_region_area_px=50))
    )
    persisted_run = run_repo.get_by_id(dto.id)
    persisted_regions = region_repo.list_by_segmentation_run_id(dto.id)

    assert persisted_run.config["min_region_area_px"] == 50
    assert persisted_run.summary["contains_deep_learning"] is False
    assert len(persisted_regions) == 1


def test_does_not_modify_dataset_release_or_audit(tmp_path):
    release_id = uuid4()
    use_case, _run_repo, _region_repo, release_repo, audit_repo, audit_run = _use_case(tmp_path, release_id)
    release_before = copy.deepcopy(release_repo.get_by_id(release_id))
    audit_before = copy.deepcopy(audit_repo.get_by_id(audit_run.id))

    use_case.execute(CreatePetriSegmentationRunRequest(release_id, audit_run.id))

    assert release_repo.get_by_id(release_id) == release_before
    assert audit_repo.get_by_id(audit_run.id) == audit_before


def test_region_persistence_failure_rolls_back_run(tmp_path):
    release_id = uuid4()
    run_repo = InMemoryPetriSegmentationRunRepository()
    region_repo = _FailingPetriSegmentationRegionRepository()
    use_case, *_ = _use_case(tmp_path, release_id, run_repo=run_repo, region_repo=region_repo)

    with pytest.raises(RuntimeError):
        use_case.execute(CreatePetriSegmentationRunRequest(release_id))

    assert run_repo.list_all() == []
    assert region_repo._by_id == {}


def test_lists_segmentation_runs_by_dataset_release_and_audit(tmp_path):
    release_id = uuid4()
    use_case, run_repo, _region_repo, _release_repo, audit_repo, audit_run = _use_case(tmp_path, release_id)
    use_case.execute(CreatePetriSegmentationRunRequest(release_id, audit_run.id))

    by_release = ListPetriSegmentationRunsUseCase(run_repo).execute(dataset_release_id=release_id)
    by_audit = ListPetriSegmentationRunsUseCase(run_repo).execute(image_audit_run_id=audit_run.id)

    assert len(by_release) == 1
    assert len(by_audit) == 1
    assert by_audit[0].image_audit_run_id == audit_run.id
