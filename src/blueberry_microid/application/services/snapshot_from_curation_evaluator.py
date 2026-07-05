from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from blueberry_microid.application.dto.dataset_curation_dto import SnapshotFromCurationPolicy
from blueberry_microid.domain.entities.dataset_curation_item import DatasetCurationItem
from blueberry_microid.domain.entities.dataset_curation_run import DatasetCurationRun
from blueberry_microid.domain.enums.dataset_curation_run_status import DatasetCurationRunStatus
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


@dataclass(frozen=True, slots=True)
class SnapshotFromCurationEvaluation:
    included_items_for_snapshot: list[DatasetCurationItem]
    skipped_items: list[DatasetCurationItem]
    warnings: list[str]
    labels_distribution: dict[str, int]
    duplicate_items_skipped: int


class SnapshotFromCurationRunEvaluator:
    """Pure eligibility evaluator for DatasetSnapshot creation from curation output."""

    _valid_review_decisions = {
        ReviewDecision.CONFIRMED,
        ReviewDecision.CORRECTED,
        ReviewDecision.MARKED_INCONCLUSIVE,
    }

    def evaluate(
        self,
        *,
        curation_run: DatasetCurationRun,
        curation_items: list[DatasetCurationItem],
        policy: SnapshotFromCurationPolicy,
    ) -> SnapshotFromCurationEvaluation:
        if (
            policy.require_completed_curation_run
            and curation_run.status != DatasetCurationRunStatus.COMPLETED
        ):
            raise ValueError("dataset curation run must be completed before snapshot creation")

        included: list[DatasetCurationItem] = []
        skipped: list[DatasetCurationItem] = []
        warnings: list[str] = []
        seen_analysis_run_ids: set[object] = set()
        duplicate_items_skipped = 0

        for item in curation_items:
            skip_reason = self._skip_reason(item, policy)
            if skip_reason is not None:
                skipped.append(item)
                warnings.append(f"{item.id}: {skip_reason}")
                continue

            if policy.prevent_duplicate_analysis_runs and item.analysis_run_id in seen_analysis_run_ids:
                skipped.append(item)
                duplicate_items_skipped += 1
                warnings.append(f"{item.id}: duplicate analysis_run_id")
                continue

            seen_analysis_run_ids.add(item.analysis_run_id)
            included.append(item)

        distribution = Counter(item.final_label.value for item in included if item.final_label is not None)
        return SnapshotFromCurationEvaluation(
            included_items_for_snapshot=included,
            skipped_items=skipped,
            warnings=warnings,
            labels_distribution=dict(sorted(distribution.items())),
            duplicate_items_skipped=duplicate_items_skipped,
        )

    def _skip_reason(self, item: DatasetCurationItem, policy: SnapshotFromCurationPolicy) -> str | None:
        if item.curation_status not in policy.include_only_status:
            return f"curation_status={item.curation_status.value} is not eligible"
        if item.curation_status != DatasetCurationStatus.INCLUDED:
            return "only included curation items can enter a snapshot"
        if policy.require_human_review_id and item.human_review_id is None:
            return "human_review_id is required"
        if policy.require_prediction_id and item.prediction_id is None:
            return "prediction_id is required"
        if policy.require_petri_image_id and item.petri_image_id is None:
            return "petri_image_id is required"
        if policy.require_micro_image_id and item.micro_image_id is None:
            return "micro_image_id is required"
        if item.sample_id is None or item.analysis_run_id is None:
            return "sample_id and analysis_run_id are required"
        if item.review_decision not in self._valid_review_decisions:
            return "review_decision is not snapshot-eligible"
        if policy.require_final_label and item.final_label is None:
            return "final_label is required"
        if item.final_label not in policy.allowed_labels:
            return "final_label is not allowed"
        if item.final_label == PredictedLabel.INCONCLUSIVE and not policy.include_inconclusive:
            return "inconclusive labels are excluded by policy"
        return None
