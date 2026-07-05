from __future__ import annotations

from dataclasses import dataclass

from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.enums.predicted_label import PredictedLabel


@dataclass(frozen=True, slots=True)
class DatasetReleaseFromSnapshotEvaluationResult:
    eligible_items: list[DatasetItem]
    skipped_items: list[DatasetItem]
    label_distribution: dict[str, int]
    warnings: list[str]


class DatasetReleaseFromSnapshotEvaluator:
    """Pure evaluator for metadata-only DatasetRelease creation.

    It never calls DatasetSplitter, creates DatasetSplitItems, copies images,
    trains models, or reads binary content.
    """

    def evaluate(
        self,
        snapshot: DatasetSnapshot,
        items: list[DatasetItem],
        *,
        include_inconclusive: bool = True,
    ) -> DatasetReleaseFromSnapshotEvaluationResult:
        allowed_labels = {label.value for label in PredictedLabel}
        eligible_items: list[DatasetItem] = []
        skipped_items: list[DatasetItem] = []
        label_distribution: dict[str, int] = {}
        warnings: list[str] = []

        for item in items:
            skip_reason = self._skip_reason(item, allowed_labels, include_inconclusive)
            if skip_reason is not None:
                skipped_items.append(item)
                warnings.append(f"{item.id}: {skip_reason}")
                continue

            eligible_items.append(item)
            label_value = item.ground_truth_label.value
            label_distribution[label_value] = label_distribution.get(label_value, 0) + 1

        return DatasetReleaseFromSnapshotEvaluationResult(
            eligible_items=eligible_items,
            skipped_items=skipped_items,
            label_distribution=dict(sorted(label_distribution.items())),
            warnings=warnings,
        )

    def _skip_reason(
        self,
        item: DatasetItem,
        allowed_labels: set[str],
        include_inconclusive: bool,
    ) -> str | None:
        if not item.included:
            return "dataset item is not included"
        if item.ground_truth_label is None:
            return "ground_truth_label is required"
        if item.ground_truth_label.value not in allowed_labels:
            return "ground_truth_label is not allowed"
        if item.ground_truth_label == PredictedLabel.INCONCLUSIVE and not include_inconclusive:
            return "inconclusive labels are excluded"
        if item.prediction_id is None or item.final_review_id is None:
            return "prediction_id and final_review_id are required"
        return None
