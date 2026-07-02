from __future__ import annotations

import logging
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from blueberry_microid.application.exceptions import DatasetSplitMetadataError
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import validate_split_ratios
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.split_strategy import SplitStrategy

logger = logging.getLogger("blueberry_microid.business.dataset_splitter")


@dataclass(frozen=True, slots=True)
class SampleSplitMetadata:
    """The subset of `Sample` fields `DatasetSplitter` needs for grouping
    strategies stricter than `by_sample`. Kept separate from the `Sample`
    entity so the splitter never has to import (or fake, in tests) the full
    entity just to know a `lot_code`/`origin` pair.
    """

    sample_id: UUID
    lot_code: Optional[str]
    origin: Optional[str]


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


def _grouping_key(
    item: DatasetItem,
    *,
    strategy: SplitStrategy,
    sample_metadata: Optional[dict[UUID, SampleSplitMetadata]],
) -> str:
    """Resolve the group a DatasetItem belongs to for the given strategy.

    Never falls back to a weaker strategy on missing metadata — raises
    `DatasetSplitMetadataError` instead, because silently substituting
    `by_sample` would hide exactly the leakage risk the caller asked to
    guard against.
    """
    if strategy == SplitStrategy.BY_SAMPLE:
        return str(item.sample_id)

    metadata = sample_metadata.get(item.sample_id) if sample_metadata else None
    if metadata is None:
        raise DatasetSplitMetadataError(
            f"sample '{item.sample_id}' metadata was not supplied, required by split_strategy='{strategy.value}'"
        )

    if strategy == SplitStrategy.BY_LOT:
        if not metadata.lot_code:
            raise DatasetSplitMetadataError(
                f"sample '{item.sample_id}' is missing lot_code, required by split_strategy='by_lot'"
            )
        return metadata.lot_code

    # SplitStrategy.BY_ORIGIN_LOT
    if not metadata.origin or not metadata.lot_code:
        raise DatasetSplitMetadataError(
            f"sample '{item.sample_id}' is missing origin and/or lot_code, "
            "required by split_strategy='by_origin_lot'"
        )
    return f"{metadata.origin}::{metadata.lot_code}"


class DatasetSplitter:
    """Deterministic train/validation/test partitioning, grouped according
    to `SplitStrategy`.

    The partition unit is never the individual DatasetItem/image — it is
    always a group: the Sample itself (`by_sample`), its lot (`by_lot`), or
    its origin+lot combination (`by_origin_lot`). Every item that resolves
    to the same group key is guaranteed to land in the same split, so no
    evidence sharing that group's conditions (a Sample's own
    Petri/microscopy evidence, or a whole lot's shared culture medium/
    protocol/contamination) can leak across train and evaluation
    partitions. Ordering never depends on incidental database/list order —
    group keys are sorted by their string form before the seeded shuffle,
    so the same `random_seed` always produces the same partition regardless
    of how `items` was fetched. Does not read image bytes, does not train
    anything, does not compute model metrics, and never balances label
    distribution artificially.
    """

    def split(
        self,
        items: list[DatasetItem],
        *,
        train_ratio: float,
        validation_ratio: float,
        test_ratio: float,
        random_seed: int,
        strategy: SplitStrategy = SplitStrategy.BY_SAMPLE,
        sample_metadata: Optional[dict[UUID, SampleSplitMetadata]] = None,
    ) -> DatasetSplitResult:
        validate_split_ratios(train_ratio, validation_ratio, test_ratio)
        if not items:
            raise ValueError("cannot split an empty list of dataset items")

        group_key_by_item_id: dict[UUID, str] = {
            item.id: _grouping_key(item, strategy=strategy, sample_metadata=sample_metadata) for item in items
        }

        items_by_group: dict[str, list[DatasetItem]] = defaultdict(list)
        for item in items:
            items_by_group[group_key_by_item_id[item.id]].append(item)

        # Sort by the group key's own string form first: a stable,
        # deterministic base ordering independent of how `items` arrived, so
        # the seeded shuffle below is reproducible across runs/processes/
        # databases.
        group_keys = sorted(items_by_group.keys())
        shuffled_group_keys = group_keys.copy()
        random.Random(random_seed).shuffle(shuffled_group_keys)

        total_groups = len(shuffled_group_keys)
        train_group_count = int(total_groups * train_ratio)
        validation_group_count = int(total_groups * validation_ratio)
        # Whatever remains goes to test (not explicitly sliced by count), so
        # every group is assigned exactly once even when the ratios don't
        # divide the total evenly.

        split_by_group_key: dict[str, DatasetSplit] = {}
        for key in shuffled_group_keys[:train_group_count]:
            split_by_group_key[key] = DatasetSplit.TRAIN
        for key in shuffled_group_keys[train_group_count : train_group_count + validation_group_count]:
            split_by_group_key[key] = DatasetSplit.VALIDATION
        for key in shuffled_group_keys[train_group_count + validation_group_count :]:
            split_by_group_key[key] = DatasetSplit.TEST

        assignments: list[DatasetSplitAssignment] = []
        # Emit assignments in a deterministic order too (by group key, then
        # item id) — independent of the caller's list order.
        for group_key in group_keys:
            for item in sorted(items_by_group[group_key], key=lambda value: str(value.id)):
                assignments.append(
                    DatasetSplitAssignment(
                        dataset_item_id=item.id,
                        sample_id=item.sample_id,
                        ground_truth_label=item.ground_truth_label,
                        split=split_by_group_key[group_key],
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
                    "split_strategy": strategy.value,
                    "group_count": total_groups,
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
