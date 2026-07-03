from __future__ import annotations

from collections import Counter, defaultdict

from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.reports.validation_report import ManifestValidationReport

_ALLOWED_SPLITS = {"train", "validation", "test"}
_ALLOWED_LABELS = {
    "no_evident_growth",
    "suspicious_growth",
    "probable_fungal_growth",
    "probable_bacterial_growth",
    "inconclusive",
}
_LOT_AWARE_STRATEGIES = {"by_lot", "by_origin_lot"}


class ManifestValidator:
    """Validate a future training manifest without training a model."""

    def validate(self, manifest: TrainingManifest, config: TrainingConfig) -> ManifestValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        leakage_checks = {
            "sample_split_isolation": True,
            "lot_split_isolation": True,
            "origin_lot_split_isolation": True,
        }

        split_counts = Counter(item.split for item in manifest.items)
        label_counts = Counter(item.ground_truth_label for item in manifest.items)
        split_label_counts: dict[str, dict[str, int]] = defaultdict(dict)
        for item in manifest.items:
            split_label_counts[item.split][item.ground_truth_label] = (
                split_label_counts[item.split].get(item.ground_truth_label, 0) + 1
            )

        if not manifest.items:
            errors.append("manifest has no items")
        for split in _ALLOWED_SPLITS:
            if split_counts.get(split, 0) == 0:
                errors.append(f"split '{split}' is empty or missing")

        analysis_run_ids: set[str] = set()
        item_keys: set[tuple[str, str, str]] = set()
        sample_splits: dict[str, str] = {}
        lot_splits: dict[str, str] = {}
        origin_lot_splits: dict[tuple[str, str], str] = {}

        for index, item in enumerate(manifest.items):
            prefix = f"item[{index}]"
            if not item.petri_image_path:
                errors.append(f"{prefix} missing petri_image_path")
            if not item.micro_image_path:
                errors.append(f"{prefix} missing micro_image_path")
            if item.split not in _ALLOWED_SPLITS:
                errors.append(f"{prefix} has invalid split '{item.split}'")
            if item.ground_truth_label not in _ALLOWED_LABELS:
                errors.append(f"{prefix} has invalid ground_truth_label '{item.ground_truth_label}'")
            if item.ground_truth_label == "inconclusive" and not config.allow_inconclusive:
                errors.append(f"{prefix} uses inconclusive but allow_inconclusive is false")

            if item.analysis_run_id in analysis_run_ids:
                errors.append(f"duplicate analysis_run_id '{item.analysis_run_id}'")
            analysis_run_ids.add(item.analysis_run_id)

            item_key = item.identity_key()
            if item_key in item_keys:
                errors.append(f"duplicate manifest item for analysis_run_id '{item.analysis_run_id}'")
            item_keys.add(item_key)

            previous_sample_split = sample_splits.setdefault(item.sample_id, item.split)
            if previous_sample_split != item.split:
                leakage_checks["sample_split_isolation"] = False
                errors.append(f"sample_id '{item.sample_id}' appears in multiple splits")

            if manifest.split_strategy == "by_lot":
                if not item.lot_code:
                    errors.append(f"{prefix} missing lot_code for by_lot split")
                else:
                    previous_lot_split = lot_splits.setdefault(item.lot_code, item.split)
                    if previous_lot_split != item.split:
                        leakage_checks["lot_split_isolation"] = False
                        errors.append(f"lot_code '{item.lot_code}' appears in multiple splits")

            if manifest.split_strategy == "by_origin_lot":
                if not item.origin or not item.lot_code:
                    errors.append(f"{prefix} missing origin or lot_code for by_origin_lot split")
                else:
                    key = (item.origin, item.lot_code)
                    previous_origin_lot_split = origin_lot_splits.setdefault(key, item.split)
                    if previous_origin_lot_split != item.split:
                        leakage_checks["origin_lot_split_isolation"] = False
                        errors.append(f"origin+lot '{item.origin}|{item.lot_code}' appears in multiple splits")

        if config.require_lot_aware_split and manifest.split_strategy not in _LOT_AWARE_STRATEGIES:
            errors.append("require_lot_aware_split requires split_strategy by_lot or by_origin_lot")
        if len(manifest.items) < config.min_total_items:
            errors.append(
                f"manifest item_count {len(manifest.items)} is below min_total_items {config.min_total_items}"
            )
        for split in _ALLOWED_SPLITS:
            count = split_counts.get(split, 0)
            if count < config.min_items_per_split:
                errors.append(f"split '{split}' has {count} items, below min_items_per_split")
        for label, count in label_counts.items():
            if label in _ALLOWED_LABELS and count < config.min_items_per_class:
                errors.append(f"label '{label}' has {count} items, below min_items_per_class")

        if len(label_counts) < 2:
            warnings.append("manifest has fewer than two labels; future training may be weak")
        if manifest.item_count != len(manifest.items):
            warnings.append("manifest declared item_count does not match items length")
        if errors:
            recommendations.append("fix manifest contract violations before any training attempt")
        else:
            recommendations.append("manifest passed pre-training validation; no model training was run")

        return ManifestValidationReport(
            is_valid=not errors,
            errors=errors,
            warnings=warnings,
            item_count=len(manifest.items),
            split_counts=dict(sorted(split_counts.items())),
            label_counts=dict(sorted(label_counts.items())),
            split_label_counts={split: dict(sorted(labels.items())) for split, labels in split_label_counts.items()},
            leakage_checks=leakage_checks,
            recommendations=recommendations,
        )

