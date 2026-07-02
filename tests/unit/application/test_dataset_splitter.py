import logging
from uuid import uuid4

import pytest

from blueberry_microid.application.services.dataset_splitter import DatasetSplitter
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import validate_split_ratios
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
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


def test_validate_split_ratios_accepts_default_ratios():
    validate_split_ratios(0.70, 0.15, 0.15)


def test_validate_split_ratios_rejects_ratios_that_do_not_sum_to_one():
    with pytest.raises(InvalidSplitRatiosError):
        validate_split_ratios(0.5, 0.3, 0.3)


def test_validate_split_ratios_rejects_out_of_range_ratio():
    with pytest.raises(InvalidSplitRatiosError):
        validate_split_ratios(1.5, -0.3, -0.2)


def test_splitter_rejects_invalid_ratios():
    splitter = DatasetSplitter()
    items = [_make_item()]
    with pytest.raises(InvalidSplitRatiosError):
        splitter.split(items, train_ratio=0.5, validation_ratio=0.3, test_ratio=0.3, random_seed=1)


def test_splitter_rejects_empty_item_list():
    splitter = DatasetSplitter()
    with pytest.raises(ValueError):
        splitter.split([], train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=1)


def test_splitter_is_deterministic_with_same_seed():
    splitter = DatasetSplitter()
    items = [_make_item() for _ in range(15)]

    result_a = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=99)
    result_b = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=99)

    assignments_a = {a.dataset_item_id: a.split for a in result_a.assignments}
    assignments_b = {a.dataset_item_id: a.split for a in result_b.assignments}
    assert assignments_a == assignments_b
    assert result_a.label_distribution == result_b.label_distribution
    assert result_a.split_distribution == result_b.split_distribution


def test_splitter_result_does_not_depend_on_input_order():
    splitter = DatasetSplitter()
    items = [_make_item() for _ in range(15)]
    reversed_items = list(reversed(items))

    result_a = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=99)
    result_b = splitter.split(reversed_items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=99)

    assignments_a = {a.dataset_item_id: a.split for a in result_a.assignments}
    assignments_b = {a.dataset_item_id: a.split for a in result_b.assignments}
    assert assignments_a == assignments_b


def test_different_seed_can_change_the_partition():
    splitter = DatasetSplitter()
    items = [_make_item() for _ in range(30)]

    result_a = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=1)
    result_b = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=2)

    assignments_a = {a.dataset_item_id: a.split for a in result_a.assignments}
    assignments_b = {a.dataset_item_id: a.split for a in result_b.assignments}
    assert assignments_a != assignments_b


def test_all_items_of_the_same_sample_land_in_the_same_split():
    splitter = DatasetSplitter()
    shared_sample_id = uuid4()
    items = [_make_item(sample_id=shared_sample_id) for _ in range(3)]
    items += [_make_item() for _ in range(12)]

    result = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=5)

    splits_for_shared_sample = {
        assignment.split for assignment in result.assignments if assignment.sample_id == shared_sample_id
    }
    assert len(splits_for_shared_sample) == 1


def test_splitter_never_duplicates_items():
    splitter = DatasetSplitter()
    items = [_make_item() for _ in range(10)]

    result = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=1)

    assert len(result.assignments) == len(items)
    assert len({a.dataset_item_id for a in result.assignments}) == len(items)


def test_splitter_handles_small_dataset_without_crashing():
    splitter = DatasetSplitter()
    items = [_make_item(), _make_item()]

    result = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=1)

    assert result.item_count == 2
    assert result.train_count + result.validation_count + result.test_count == 2


def test_splitter_logs_a_warning_when_a_split_ends_up_empty(caplog):
    splitter = DatasetSplitter()
    items = [_make_item(), _make_item()]

    with caplog.at_level(logging.WARNING, logger="blueberry_microid.business.dataset_splitter"):
        splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=1)

    assert "empty partition" in caplog.text


def test_splitter_sample_level_counts_are_independent_of_seed():
    splitter = DatasetSplitter()
    items = [_make_item() for _ in range(10)]

    result_seed_1 = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=1)
    result_seed_2 = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=2)

    for result in (result_seed_1, result_seed_2):
        assert result.train_count == 7
        assert result.validation_count == 1
        assert result.test_count == 2


def test_splitter_computes_label_and_split_distribution():
    splitter = DatasetSplitter()
    items = [_make_item(label=PredictedLabel.NO_EVIDENT_GROWTH) for _ in range(5)]
    items += [_make_item(label=PredictedLabel.SUSPICIOUS_GROWTH) for _ in range(5)]

    result = splitter.split(items, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=1)

    assert result.label_distribution == {"no_evident_growth": 5, "suspicious_growth": 5}
    total_from_split_distribution = sum(
        count for split_counts in result.split_distribution.values() for count in split_counts.values()
    )
    assert total_from_split_distribution == 10
