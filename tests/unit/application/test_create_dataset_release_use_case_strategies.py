from uuid import uuid4

import pytest

from blueberry_microid.application.dto.dataset_dto import CreateDatasetReleaseRequest, CreateDatasetSnapshotRequest
from blueberry_microid.application.exceptions import DatasetSplitMetadataError
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
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
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


class _FailingDatasetSplitItemRepository(InMemoryDatasetSplitItemRepository):
    """Always raises on add_many(), to prove the use case propagates the
    failure instead of swallowing it or committing partial state."""

    def add_many(self, dataset_split_items):
        raise RuntimeError("simulated database failure")


def _make_context(*, split_item_repo=None):
    sample_repo = InMemorySampleRepository()
    petri_repo = InMemoryPetriImageRepository()
    micro_repo = InMemoryMicroImageRepository()
    analysis_repo = InMemoryAnalysisRunRepository()
    prediction_repo = InMemoryPredictionRepository()
    review_repo = InMemoryHumanReviewRepository()
    snapshot_repo = InMemoryDatasetSnapshotRepository()
    item_repo = InMemoryDatasetItemRepository()
    release_repo = InMemoryDatasetReleaseRepository()
    split_item_repo = split_item_repo or InMemoryDatasetSplitItemRepository()
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
    release_use_case = CreateDatasetReleaseUseCase(snapshot_repo, item_repo, sample_repo, DatasetSplitter(), uow)
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
        "uow": uow,
    }


def _add_reviewed_run(
    ctx,
    *,
    sample_code: str,
    lot_code: str | None = None,
    origin: str | None = None,
    prediction_label: PredictedLabel = PredictedLabel.SUSPICIOUS_GROWTH,
):
    sample = Sample(sample_code=sample_code, lot_code=lot_code, origin=origin)
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
    return sample, run


def _create_snapshot(ctx):
    return ctx["snapshot_use_case"].execute(CreateDatasetSnapshotRequest(name="curated", version=str(uuid4())))


def _create_release(ctx, dataset_snapshot_id, **kwargs):
    defaults = {"dataset_snapshot_id": dataset_snapshot_id, "name": "release", "version": str(uuid4())}
    defaults.update(kwargs)
    return ctx["release_use_case"].execute(CreateDatasetReleaseRequest(**defaults))


def test_creates_release_with_by_sample_strategy():
    ctx = _make_context()
    for i in range(10):
        _add_reviewed_run(ctx, sample_code=f"BB-{i:03d}")
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, split_strategy=SplitStrategy.BY_SAMPLE)

    assert release.split_strategy == SplitStrategy.BY_SAMPLE
    assert release.item_count == 10


def test_creates_release_with_by_lot_strategy():
    ctx = _make_context()
    for lot in range(5):
        for sample_index in range(2):
            _add_reviewed_run(ctx, sample_code=f"BB-L{lot}-{sample_index}", lot_code=f"LOT-{lot}")
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, split_strategy=SplitStrategy.BY_LOT)

    assert release.split_strategy == SplitStrategy.BY_LOT
    assert release.item_count == 10
    split_items = ctx["split_item_repo"].list_by_dataset_release_id(release.id)
    splits_by_lot: dict = {}
    for item in split_items:
        lot_code = ctx["sample_repo"].get_by_id(item.sample_id).lot_code
        splits_by_lot.setdefault(lot_code, set()).add(item.split)
    assert all(len(splits) == 1 for splits in splits_by_lot.values())


def test_creates_release_with_by_origin_lot_strategy():
    ctx = _make_context()
    for lot in range(5):
        for sample_index in range(2):
            _add_reviewed_run(
                ctx,
                sample_code=f"BB-OL{lot}-{sample_index}",
                lot_code=f"LOT-{lot}",
                origin=f"ORIGIN-{lot % 2}",
            )
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, split_strategy=SplitStrategy.BY_ORIGIN_LOT)

    assert release.split_strategy == SplitStrategy.BY_ORIGIN_LOT
    assert release.item_count == 10
    split_items = ctx["split_item_repo"].list_by_dataset_release_id(release.id)
    splits_by_group: dict = {}
    for item in split_items:
        sample = ctx["sample_repo"].get_by_id(item.sample_id)
        splits_by_group.setdefault((sample.origin, sample.lot_code), set()).add(item.split)
    assert all(len(splits) == 1 for splits in splits_by_group.values())


def test_rejects_by_lot_when_a_sample_has_no_lot_code():
    ctx = _make_context()
    _add_reviewed_run(ctx, sample_code="BB-NOLOT", lot_code=None)
    snapshot = _create_snapshot(ctx)

    with pytest.raises(DatasetSplitMetadataError):
        _create_release(ctx, snapshot.id, split_strategy=SplitStrategy.BY_LOT)


def test_rejects_by_origin_lot_when_a_sample_is_missing_metadata():
    ctx = _make_context()
    _add_reviewed_run(ctx, sample_code="BB-NOORIGIN", lot_code="LOT-1", origin=None)
    snapshot = _create_snapshot(ctx)

    with pytest.raises(DatasetSplitMetadataError):
        _create_release(ctx, snapshot.id, split_strategy=SplitStrategy.BY_ORIGIN_LOT)


def test_split_strategy_is_persisted_on_the_release():
    ctx = _make_context()
    for i in range(3):
        _add_reviewed_run(ctx, sample_code=f"BB-P{i}", lot_code=f"LOT-{i}")
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, split_strategy=SplitStrategy.BY_LOT)

    persisted = ctx["release_repo"].get_by_id(release.id)
    assert persisted.split_strategy == SplitStrategy.BY_LOT


def test_split_distribution_is_calculated_correctly():
    ctx = _make_context()
    for i in range(10):
        _add_reviewed_run(ctx, sample_code=f"BB-D{i}", prediction_label=PredictedLabel.SUSPICIOUS_GROWTH)
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, random_seed=1)

    total_from_split_distribution = sum(
        count for split_counts in release.split_distribution.values() for count in split_counts.values()
    )
    assert total_from_split_distribution == release.item_count


def test_label_distribution_stays_correct():
    ctx = _make_context()
    for i in range(5):
        _add_reviewed_run(ctx, sample_code=f"BB-LD1-{i}", prediction_label=PredictedLabel.NO_EVIDENT_GROWTH)
    for i in range(5):
        _add_reviewed_run(ctx, sample_code=f"BB-LD2-{i}", prediction_label=PredictedLabel.SUSPICIOUS_GROWTH)
    snapshot = _create_snapshot(ctx)

    release = _create_release(ctx, snapshot.id, random_seed=1)

    assert release.label_distribution == {"no_evident_growth": 5, "suspicious_growth": 5}


def test_transaction_does_not_commit_when_split_item_creation_fails():
    failing_split_item_repo = _FailingDatasetSplitItemRepository()
    ctx = _make_context(split_item_repo=failing_split_item_repo)
    for i in range(3):
        _add_reviewed_run(ctx, sample_code=f"BB-TX{i}")
    snapshot = _create_snapshot(ctx)
    # `committed` is a cumulative flag on the shared fake UoW and the
    # snapshot creation above legitimately committed — reset it so the
    # assertion below is only about the release attempt that follows.
    ctx["uow"].committed = False

    with pytest.raises(RuntimeError):
        _create_release(ctx, snapshot.id)

    assert ctx["uow"].committed is False


def test_creating_a_by_lot_release_does_not_modify_snapshot_or_items():
    ctx = _make_context()
    _add_reviewed_run(ctx, sample_code="BB-IMM", lot_code="LOT-1")
    snapshot = _create_snapshot(ctx)
    original_item_count = snapshot.item_count
    original_items = ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id)

    _create_release(ctx, snapshot.id, split_strategy=SplitStrategy.BY_LOT)

    assert ctx["snapshot_repo"].get_by_id(snapshot.id).item_count == original_item_count
    assert ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id) == original_items
