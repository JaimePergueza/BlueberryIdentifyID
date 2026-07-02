from uuid import uuid4

import pytest

from blueberry_microid.application.exceptions import DatasetSplitMetadataError
from blueberry_microid.application.services.dataset_splitter import DatasetSplitter, SampleSplitMetadata
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from blueberry_microid.domain.exceptions.errors import InvalidSplitRatiosError


def _make_item(sample_id=None, label: PredictedLabel = PredictedLabel.NO_EVIDENT_GROWTH) -> DatasetItem:
    return DatasetItem(
        dataset_snapshot_id=uuid4(),
        analysis_run_id=uuid4(),
        sample_id=sample_id or uuid4(),
        petri_image_id=uuid4(),
        micro_image_id=uuid4(),
        prediction_id=uuid4(),
        final_review_id=uuid4(),
        source_review_decision=ReviewDecision.CONFIRMED,
        ground_truth_label=label,
    )


def _build_lots(num_lots: int, samples_per_lot: int, *, with_origin: bool = False):
    """Build (items, sample_metadata) for `num_lots` lots, each with
    `samples_per_lot` distinct Samples and one DatasetItem per Sample."""
    items: list[DatasetItem] = []
    sample_metadata: dict = {}
    for lot_index in range(num_lots):
        lot_code = f"LOT-{lot_index}"
        origin = f"ORIGIN-{lot_index % 2}" if with_origin else None
        for _ in range(samples_per_lot):
            sample_id = uuid4()
            sample_metadata[sample_id] = SampleSplitMetadata(sample_id=sample_id, lot_code=lot_code, origin=origin)
            items.append(_make_item(sample_id=sample_id))
    return items, sample_metadata


def test_by_sample_strategy_matches_default_behavior():
    splitter = DatasetSplitter()
    items = [_make_item() for _ in range(15)]

    result_default = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=99)
    result_explicit = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=99,
        strategy=SplitStrategy.BY_SAMPLE,
    )

    assignments_default = {a.dataset_item_id: a.split for a in result_default.assignments}
    assignments_explicit = {a.dataset_item_id: a.split for a in result_explicit.assignments}
    assert assignments_default == assignments_explicit


def test_by_lot_keeps_all_samples_of_the_same_lot_together():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=10, samples_per_lot=3)

    result = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=1,
        strategy=SplitStrategy.BY_LOT,
        sample_metadata=sample_metadata,
    )

    splits_by_lot: dict = {}
    for assignment in result.assignments:
        lot_code = sample_metadata[assignment.sample_id].lot_code
        splits_by_lot.setdefault(lot_code, set()).add(assignment.split)
    assert all(len(splits) == 1 for splits in splits_by_lot.values())


def test_by_origin_lot_keeps_all_samples_of_the_same_origin_and_lot_together():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=10, samples_per_lot=3, with_origin=True)

    result = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=1,
        strategy=SplitStrategy.BY_ORIGIN_LOT,
        sample_metadata=sample_metadata,
    )

    splits_by_group: dict = {}
    for assignment in result.assignments:
        metadata = sample_metadata[assignment.sample_id]
        group_key = (metadata.origin, metadata.lot_code)
        splits_by_group.setdefault(group_key, set()).add(assignment.split)
    assert all(len(splits) == 1 for splits in splits_by_group.values())


def test_by_lot_fails_when_a_sample_is_missing_lot_code():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=3, samples_per_lot=2)
    some_sample_id = next(iter(sample_metadata))
    sample_metadata[some_sample_id] = SampleSplitMetadata(sample_id=some_sample_id, lot_code=None, origin=None)

    with pytest.raises(DatasetSplitMetadataError):
        splitter.split(
            items,
            train_ratio=0.7,
            validation_ratio=0.15,
            test_ratio=0.15,
            random_seed=1,
            strategy=SplitStrategy.BY_LOT,
            sample_metadata=sample_metadata,
        )


def test_by_origin_lot_fails_when_a_sample_is_missing_origin():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=3, samples_per_lot=2, with_origin=True)
    some_sample_id = next(iter(sample_metadata))
    metadata = sample_metadata[some_sample_id]
    sample_metadata[some_sample_id] = SampleSplitMetadata(
        sample_id=some_sample_id, lot_code=metadata.lot_code, origin=None
    )

    with pytest.raises(DatasetSplitMetadataError):
        splitter.split(
            items,
            train_ratio=0.7,
            validation_ratio=0.15,
            test_ratio=0.15,
            random_seed=1,
            strategy=SplitStrategy.BY_ORIGIN_LOT,
            sample_metadata=sample_metadata,
        )


def test_by_origin_lot_fails_when_a_sample_is_missing_lot_code():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=3, samples_per_lot=2, with_origin=True)
    some_sample_id = next(iter(sample_metadata))
    metadata = sample_metadata[some_sample_id]
    sample_metadata[some_sample_id] = SampleSplitMetadata(
        sample_id=some_sample_id, lot_code=None, origin=metadata.origin
    )

    with pytest.raises(DatasetSplitMetadataError):
        splitter.split(
            items,
            train_ratio=0.7,
            validation_ratio=0.15,
            test_ratio=0.15,
            random_seed=1,
            strategy=SplitStrategy.BY_ORIGIN_LOT,
            sample_metadata=sample_metadata,
        )


def test_by_lot_fails_when_sample_metadata_is_not_supplied_at_all():
    splitter = DatasetSplitter()
    items, _ = _build_lots(num_lots=3, samples_per_lot=2)

    with pytest.raises(DatasetSplitMetadataError):
        splitter.split(
            items,
            train_ratio=0.7,
            validation_ratio=0.15,
            test_ratio=0.15,
            random_seed=1,
            strategy=SplitStrategy.BY_LOT,
        )


def test_by_lot_is_deterministic_with_same_seed():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=10, samples_per_lot=2)

    result_a = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=5,
        strategy=SplitStrategy.BY_LOT,
        sample_metadata=sample_metadata,
    )
    result_b = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=5,
        strategy=SplitStrategy.BY_LOT,
        sample_metadata=sample_metadata,
    )

    assignments_a = {a.dataset_item_id: a.split for a in result_a.assignments}
    assignments_b = {a.dataset_item_id: a.split for a in result_b.assignments}
    assert assignments_a == assignments_b


def test_by_lot_different_seed_can_change_partition():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=20, samples_per_lot=2)

    result_a = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=1,
        strategy=SplitStrategy.BY_LOT,
        sample_metadata=sample_metadata,
    )
    result_b = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=2,
        strategy=SplitStrategy.BY_LOT,
        sample_metadata=sample_metadata,
    )

    assignments_a = {a.dataset_item_id: a.split for a in result_a.assignments}
    assignments_b = {a.dataset_item_id: a.split for a in result_b.assignments}
    assert assignments_a != assignments_b


def test_by_lot_rejects_invalid_ratios():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=3, samples_per_lot=2)

    with pytest.raises(InvalidSplitRatiosError):
        splitter.split(
            items,
            train_ratio=0.5,
            validation_ratio=0.3,
            test_ratio=0.3,
            random_seed=1,
            strategy=SplitStrategy.BY_LOT,
            sample_metadata=sample_metadata,
        )


def test_by_lot_result_does_not_depend_on_input_order():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=10, samples_per_lot=2)
    reversed_items = list(reversed(items))

    result_a = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=42,
        strategy=SplitStrategy.BY_LOT,
        sample_metadata=sample_metadata,
    )
    result_b = splitter.split(
        reversed_items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=42,
        strategy=SplitStrategy.BY_LOT,
        sample_metadata=sample_metadata,
    )

    assignments_a = {a.dataset_item_id: a.split for a in result_a.assignments}
    assignments_b = {a.dataset_item_id: a.split for a in result_b.assignments}
    assert assignments_a == assignments_b


def test_by_lot_never_duplicates_items_and_assigns_each_exactly_once():
    splitter = DatasetSplitter()
    items, sample_metadata = _build_lots(num_lots=10, samples_per_lot=3)

    result = splitter.split(
        items,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=1,
        strategy=SplitStrategy.BY_LOT,
        sample_metadata=sample_metadata,
    )

    assert len(result.assignments) == len(items)
    assert len({a.dataset_item_id for a in result.assignments}) == len(items)
