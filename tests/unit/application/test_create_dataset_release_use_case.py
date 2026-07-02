from uuid import uuid4

import pytest

from blueberry_microid.application.dto.dataset_dto import CreateDatasetReleaseRequest, CreateDatasetSnapshotRequest
from blueberry_microid.application.exceptions import DatasetSnapshotNotFoundError, EmptyDatasetSnapshotError
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.application.services.dataset_splitter import DatasetSplitter
from blueberry_microid.application.use_cases.dataset.create_dataset_release import CreateDatasetReleaseUseCase
from blueberry_microid.application.use_cases.dataset.create_dataset_snapshot import CreateDatasetSnapshotUseCase
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.exceptions.errors import InvalidSplitRatiosError
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetItemRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryDatasetSnapshotRepository,
    InMemoryDatasetSplitItemRepository,
    InMemoryHumanReviewRepository,
    InMemoryMicroImageRepository,
    InMemoryPetriImageRepository,
    InMemoryPredictionRepository,
    InMemorySampleRepository,
)


def _make_context():
    sample_repo = InMemorySampleRepository()
    petri_repo = InMemoryPetriImageRepository()
    micro_repo = InMemoryMicroImageRepository()
    analysis_repo = InMemoryAnalysisRunRepository()
    prediction_repo = InMemoryPredictionRepository()
    review_repo = InMemoryHumanReviewRepository()
    snapshot_repo = InMemoryDatasetSnapshotRepository()
    item_repo = InMemoryDatasetItemRepository()
    release_repo = InMemoryDatasetReleaseRepository()
    split_item_repo = InMemoryDatasetSplitItemRepository()
    uow = FakeUnitOfWork(
        analysis_repo,
        prediction_repo,
        review_repo,
        dataset_snapshot_repository=snapshot_repo,
        dataset_item_repository=item_repo,
        dataset_release_repository=release_repo,
        dataset_split_item_repository=split_item_repo,
    )
    snapshot_use_case = CreateDatasetSnapshotUseCase(
        analysis_repo, prediction_repo, review_repo, petri_repo, micro_repo, uow
    )
    release_use_case = CreateDatasetReleaseUseCase(snapshot_repo, item_repo, DatasetSplitter(), uow)
    return {
        "sample_repo": sample_repo,
        "petri_repo": petri_repo,
        "micro_repo": micro_repo,
        "analysis_repo": analysis_repo,
        "prediction_repo": prediction_repo,
        "review_repo": review_repo,
        "snapshot_repo": snapshot_repo,
        "item_repo": item_repo,
        "release_repo": release_repo,
        "split_item_repo": split_item_repo,
        "snapshot_use_case": snapshot_use_case,
        "release_use_case": release_use_case,
    }


def _add_reviewed_run(ctx, *, sample_code: str, prediction_label: PredictedLabel = PredictedLabel.SUSPICIOUS_GROWTH):
    sample = Sample(sample_code=sample_code)
    ctx["sample_repo"].add(sample)
    petri = PetriImage(
        sample_id=sample.id, file_path=f"petri/{sample_code}.jpg", file_name=f"{sample_code}.jpg",
        mime_type="image/jpeg", file_size_bytes=10,
    )
    micro = MicroImage(
        sample_id=sample.id, file_path=f"micro/{sample_code}.png", file_name=f"{sample_code}.png",
        mime_type="image/png", file_size_bytes=10,
    )
    ctx["petri_repo"].add(petri)
    ctx["micro_repo"].add(micro)
    return sample, _add_analysis_run_for(ctx, sample, petri, micro, prediction_label=prediction_label)


def _add_analysis_run_for(ctx, sample, petri, micro, *, prediction_label: PredictedLabel):
    run = AnalysisRun(
        sample_id=sample.id, petri_image_id=petri.id, micro_image_id=micro.id,
        model_version_id=uuid4(), status=AnalysisStatus.COMPLETED,
    )
    ctx["analysis_repo"].add(run)
    prediction = Prediction(analysis_run_id=run.id, predicted_label=prediction_label, confidence_score=0.5)
    ctx["prediction_repo"].add(prediction)
    review = HumanReview(
        analysis_run_id=run.id, reviewer_name="expert", review_decision=ReviewDecision.CONFIRMED, is_final=True
    )
    ctx["review_repo"].add(review)
    return run


def _create_snapshot(ctx):
    return ctx["snapshot_use_case"].execute(CreateDatasetSnapshotRequest(name="curated", version=str(uuid4())))


def _create_release(ctx, dataset_snapshot_id, **kwargs):
    defaults = {"dataset_snapshot_id": dataset_snapshot_id, "name": "release", "version": str(uuid4())}
    defaults.update(kwargs)
    return ctx["release_use_case"].execute(CreateDatasetReleaseRequest(**defaults))


def test_create_release_rejects_missing_snapshot():
    ctx = _make_context()

    with pytest.raises(DatasetSnapshotNotFoundError):
        _create_release(ctx, uuid4())


def test_create_release_rejects_empty_snapshot():
    ctx = _make_context()
    snapshot = _create_snapshot(ctx)  # no analysis runs added: item_count == 0

    with pytest.raises(EmptyDatasetSnapshotError):
        _create_release(ctx, snapshot.id)


def test_create_release_rejects_invalid_ratios():
    ctx = _make_context()
    _add_reviewed_run(ctx, sample_code="BB-001")
    snapshot = _create_snapshot(ctx)

    with pytest.raises(InvalidSplitRatiosError):
        _create_release(ctx, snapshot.id, train_ratio=0.5, validation_ratio=0.3, test_ratio=0.3)


def test_create_release_produces_correct_counts():
    ctx = _make_context()
    for i in range(10):
        _add_reviewed_run(ctx, sample_code=f"BB-{i:03d}")
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, random_seed=1)

    assert release.item_count == 10
    assert release.train_count == 7
    assert release.validation_count == 1
    assert release.test_count == 2
    assert release.train_count + release.validation_count + release.test_count == release.item_count


def test_create_release_does_not_duplicate_dataset_items():
    ctx = _make_context()
    for i in range(10):
        _add_reviewed_run(ctx, sample_code=f"BB-{i:03d}")
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, random_seed=1)

    split_items = ctx["split_item_repo"].list_by_dataset_release_id(release.id)
    assert len(split_items) == 10
    assert len({item.dataset_item_id for item in split_items}) == 10


def test_create_release_keeps_all_items_of_a_sample_together():
    ctx = _make_context()
    sample = Sample(sample_code="BB-MULTI")
    ctx["sample_repo"].add(sample)
    petri = PetriImage(
        sample_id=sample.id, file_path="petri/multi.jpg", file_name="multi.jpg",
        mime_type="image/jpeg", file_size_bytes=10,
    )
    micro = MicroImage(
        sample_id=sample.id, file_path="micro/multi.png", file_name="multi.png",
        mime_type="image/png", file_size_bytes=10,
    )
    ctx["petri_repo"].add(petri)
    ctx["micro_repo"].add(micro)
    for _ in range(2):
        _add_analysis_run_for(ctx, sample, petri, micro, prediction_label=PredictedLabel.SUSPICIOUS_GROWTH)
    for i in range(9):
        _add_reviewed_run(ctx, sample_code=f"BB-{i:03d}")
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, random_seed=7)

    split_items = ctx["split_item_repo"].list_by_dataset_release_id(release.id)
    same_sample_splits = {item.split for item in split_items if item.sample_id == sample.id}
    assert len(same_sample_splits) == 1


def test_create_release_is_deterministic_with_same_seed():
    ctx = _make_context()
    for i in range(10):
        _add_reviewed_run(ctx, sample_code=f"BB-{i:03d}")
    snapshot = _create_snapshot(ctx)

    release_a = _create_release(ctx, snapshot.id, name="release-a", version="1", random_seed=123)
    release_b = _create_release(ctx, snapshot.id, name="release-b", version="2", random_seed=123)

    splits_a = {item.dataset_item_id: item.split for item in ctx["split_item_repo"].list_by_dataset_release_id(release_a.id)}
    splits_b = {item.dataset_item_id: item.split for item in ctx["split_item_repo"].list_by_dataset_release_id(release_b.id)}
    assert splits_a == splits_b
    assert release_a.label_distribution == release_b.label_distribution
    assert release_a.split_distribution == release_b.split_distribution


def test_create_release_different_seed_can_change_partition():
    ctx = _make_context()
    for i in range(20):
        _add_reviewed_run(ctx, sample_code=f"BB-{i:03d}")
    snapshot = _create_snapshot(ctx)

    release_a = _create_release(ctx, snapshot.id, name="release-a", version="1", random_seed=1)
    release_b = _create_release(ctx, snapshot.id, name="release-b", version="2", random_seed=2)

    splits_a = {item.dataset_item_id: item.split for item in ctx["split_item_repo"].list_by_dataset_release_id(release_a.id)}
    splits_b = {item.dataset_item_id: item.split for item in ctx["split_item_repo"].list_by_dataset_release_id(release_b.id)}
    assert splits_a != splits_b


def test_create_release_does_not_modify_snapshot_or_items():
    ctx = _make_context()
    _add_reviewed_run(ctx, sample_code="BB-001")
    snapshot = _create_snapshot(ctx)
    original_item_count = snapshot.item_count
    original_items = ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id)

    _create_release(ctx, snapshot.id)

    assert ctx["snapshot_repo"].get_by_id(snapshot.id).item_count == original_item_count
    assert ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id) == original_items


def test_create_release_manifest_is_deterministic_and_free_of_taxonomy():
    ctx = _make_context()
    for i in range(5):
        _add_reviewed_run(ctx, sample_code=f"BB-{i:03d}")
    snapshot = _create_snapshot(ctx)
    release = _create_release(ctx, snapshot.id, random_seed=42)
    exporter = DatasetReleaseManifestExporter(
        ctx["release_repo"],
        ctx["split_item_repo"],
        ctx["item_repo"],
        ctx["sample_repo"],
        ctx["petri_repo"],
        ctx["micro_repo"],
        ctx["prediction_repo"],
    )

    manifest_a = exporter.export(release.id)
    manifest_b = exporter.export(release.id)

    assert manifest_a == manifest_b
    splits_seen = [item["split"] for item in manifest_a["items"]]
    assert splits_seen == sorted(splits_seen)
    assert "species" not in str(manifest_a).lower()
    assert "genus" not in str(manifest_a).lower()
    assert "binary" not in str(manifest_a).lower()
