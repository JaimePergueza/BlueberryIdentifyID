from __future__ import annotations

import logging
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import validate_split_ratios
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel

logger = logging.getLogger("blueberry_microid.business.dataset_splitter")


@dataclass(frozen=True, slots=True)
class DatasetSplitAssignment:
    """One DatasetItem's computed split, before any DatasetRelease exists to
    attach it to (the release only gets an id once it is constructed by the
    use case, after splitting)."""

    dataset_item_id: UUID
    sample_id: UUID
    ground_truth_label: Optional[PredictedLabel]
    split: DatasetSplit


@dataclass(frozen=True, slots=True)
class DatasetSplitResult:
    assignments: list[DatasetSplitAssignment]
    item_count: int
    train_count: int
    validation_count: int
    test_count: int
    label_distribution: dict[str, int]
    split_distribution: dict[str, dict[str, int]]


class DatasetSplitter:
    """Deterministic, Sample-level train/validation/test partitioning.

    The partition unit is always the Sample, never the individual
    DatasetItem/image: every item that shares a `sample_id` is guaranteed to
    land in the same split, so no Petri/microscopy evidence from one Sample
    can leak across train and evaluation partitions. Ordering never depends
    on incidental database/list order — sample ids are sorted by their
    string form before the seeded shuffle, so the same `random_seed` always
    produces the same partition regardless of how `items` was fetched. Does
    not read image bytes, does not train anything, does not compute model
    metrics, and never balances label distribution artificially.
    """

    def split(
        self,
        items: list[DatasetItem],
        *,
        train_ratio: float,
        validation_ratio: float,
        test_ratio: float,
        random_seed: int,
    ) -> DatasetSplitResult:
        validate_split_ratios(train_ratio, validation_ratio, test_ratio)
        if not items:
            raise ValueError("cannot split an empty list of dataset items")

        items_by_sample: dict[UUID, list[DatasetItem]] = defaultdict(list)
        for item in items:
            items_by_sample[item.sample_id].append(item)

        # Sort by the string form of the UUID first: a stable, deterministic
        # base ordering independent of how `items` arrived, so the seeded
        # shuffle below is reproducible across runs/processes/databases.
        sample_ids = sorted(items_by_sample.keys(), key=str)
        shuffled_sample_ids = sample_ids.copy()
        random.Random(random_seed).shuffle(shuffled_sample_ids)

        total_samples = len(shuffled_sample_ids)
        train_sample_count = int(total_samples * train_ratio)
        validation_sample_count = int(total_samples * validation_ratio)
        # Whatever remains goes to test (not explicitly sliced by count), so
        # every sample is assigned exactly once even when the ratios don't
        # divide the total evenly.

        split_by_sample_id: dict[UUID, DatasetSplit] = {}
        for sample_id in shuffled_sample_ids[:train_sample_count]:
            split_by_sample_id[sample_id] = DatasetSplit.TRAIN
        for sample_id in shuffled_sample_ids[train_sample_count : train_sample_count + validation_sample_count]:
            split_by_sample_id[sample_id] = DatasetSplit.VALIDATION
        for sample_id in shuffled_sample_ids[train_sample_count + validation_sample_count :]:
            split_by_sample_id[sample_id] = DatasetSplit.TEST

        assignments: list[DatasetSplitAssignment] = []
        # Emit assignments in a deterministic order too (by sample id, then
        # item id) — independent of the caller's list order.
        for sample_id in sample_ids:
            for item in sorted(items_by_sample[sample_id], key=lambda value: str(value.id)):
                assignments.append(
                    DatasetSplitAssignment(
                        dataset_item_id=item.id,
                        sample_id=item.sample_id,
                        ground_truth_label=item.ground_truth_label,
                        split=split_by_sample_id[sample_id],
                    )
                )

        label_distribution = Counter(
            assignment.ground_truth_label.value for assignment in assignments if assignment.ground_truth_label
        )
        split_distribution: dict[str, Counter] = defaultdict(Counter)
        for assignment in assignments:
            if assignment.ground_truth_label:
                split_distribution[assignment.split.value][assignment.ground_truth_label.value] += 1

        train_count = sum(1 for assignment in assignments if assignment.split == DatasetSplit.TRAIN)
        validation_count = sum(1 for assignment in assignments if assignment.split == DatasetSplit.VALIDATION)
        test_count = sum(1 for assignment in assignments if assignment.split == DatasetSplit.TEST)

        if len(assignments) > 0 and (train_count == 0 or validation_count == 0 or test_count == 0):
            logger.warning(
                "dataset release split produced at least one empty partition "
                "(dataset too small relative to the configured ratios)",
                extra={
                    "sample_count": total_samples,
                    "item_count": len(assignments),
                    "train_count": train_count,
                    "validation_count": validation_count,
                    "test_count": test_count,
                },
            )

        return DatasetSplitResult(
            assignments=assignments,
            item_count=len(assignments),
            train_count=train_count,
            validation_count=validation_count,
            test_count=test_count,
            label_distribution=dict(sorted(label_distribution.items())),
            split_distribution={
                split_value: dict(sorted(counter.items()))
                for split_value, counter in sorted(split_distribution.items())
            },
        )
