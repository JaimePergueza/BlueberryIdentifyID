from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import numpy as np

from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.entities.image_feature_vector import ImageFeatureVector
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.configs.tabular_feature_training_config import TabularFeatureTrainingConfig

_SPLIT_ORDER = [DatasetSplit.TRAIN, DatasetSplit.VALIDATION, DatasetSplit.TEST]
_MODALITY_ORDER = [ImageModality.PETRI, ImageModality.MICRO]


@dataclass(frozen=True, slots=True)
class FeatureMatrixItemRef:
    dataset_split_item_id: UUID
    dataset_item_id: UUID
    split: DatasetSplit


@dataclass(frozen=True, slots=True)
class FeatureMatrix:
    X_train: np.ndarray
    y_train: list[PredictedLabel]
    X_validation: np.ndarray
    y_validation: list[PredictedLabel]
    X_test: np.ndarray
    y_test: list[PredictedLabel]
    feature_names: list[str]
    train_refs: list[FeatureMatrixItemRef]
    validation_refs: list[FeatureMatrixItemRef]
    test_refs: list[FeatureMatrixItemRef]


class FeatureMatrixBuilder:
    """Builds deterministic tabular matrices from persisted ImageFeatureVector."""

    def build(
        self,
        feature_vectors: list[ImageFeatureVector],
        split_items: list[DatasetSplitItem],
        config: TabularFeatureTrainingConfig,
    ) -> FeatureMatrix:
        vectors_by_split_item: dict[UUID, dict[ImageModality, ImageFeatureVector]] = {}
        for vector in feature_vectors:
            vectors_by_split_item.setdefault(vector.dataset_split_item_id, {})[vector.modality] = vector

        eligible_split_items = [
            item
            for item in sorted(split_items, key=lambda i: (_SPLIT_ORDER.index(i.split), str(i.id)))
            if self._is_allowed_label(item, config)
        ]
        if not eligible_split_items:
            raise ValueError("no dataset split items are eligible for tabular feature training")

        raw_rows = []
        for split_item in eligible_split_items:
            modality_vectors = vectors_by_split_item.get(split_item.id, {})
            row = self._row_for_split_item(split_item, modality_vectors, config)
            raw_rows.append((split_item, row))

        feature_names = sorted({name for _split_item, row in raw_rows for name in row})
        if not feature_names:
            raise ValueError("no numeric tabular features were found")

        rows_by_split: dict[DatasetSplit, list[list[float]]] = {split: [] for split in _SPLIT_ORDER}
        labels_by_split: dict[DatasetSplit, list[PredictedLabel]] = {split: [] for split in _SPLIT_ORDER}
        refs_by_split: dict[DatasetSplit, list[FeatureMatrixItemRef]] = {split: [] for split in _SPLIT_ORDER}

        for split_item, row in raw_rows:
            missing = [name for name in feature_names if name not in row]
            if missing and config.fail_on_missing_feature:
                raise ValueError(
                    f"missing tabular features for dataset_split_item '{split_item.id}': {', '.join(missing)}"
                )
            rows_by_split[split_item.split].append([float(row.get(name, 0.0)) for name in feature_names])
            assert split_item.ground_truth_label is not None
            labels_by_split[split_item.split].append(PredictedLabel(split_item.ground_truth_label.value))
            refs_by_split[split_item.split].append(
                FeatureMatrixItemRef(
                    dataset_split_item_id=split_item.id,
                    dataset_item_id=split_item.dataset_item_id,
                    split=split_item.split,
                )
            )

        return FeatureMatrix(
            X_train=self._as_array(rows_by_split[DatasetSplit.TRAIN], feature_names),
            y_train=labels_by_split[DatasetSplit.TRAIN],
            X_validation=self._as_array(rows_by_split[DatasetSplit.VALIDATION], feature_names),
            y_validation=labels_by_split[DatasetSplit.VALIDATION],
            X_test=self._as_array(rows_by_split[DatasetSplit.TEST], feature_names),
            y_test=labels_by_split[DatasetSplit.TEST],
            feature_names=feature_names,
            train_refs=refs_by_split[DatasetSplit.TRAIN],
            validation_refs=refs_by_split[DatasetSplit.VALIDATION],
            test_refs=refs_by_split[DatasetSplit.TEST],
        )

    def _row_for_split_item(
        self,
        split_item: DatasetSplitItem,
        modality_vectors: dict[ImageModality, ImageFeatureVector],
        config: TabularFeatureTrainingConfig,
    ) -> dict[str, float]:
        row: dict[str, float] = {}
        for modality in _selected_modalities(config):
            vector = modality_vectors.get(modality)
            if vector is None:
                if config.fail_on_missing_feature:
                    raise ValueError(f"missing {modality.value} features for dataset_split_item '{split_item.id}'")
                continue
            row.update(_flatten_features(vector.features, prefix=f"{modality.value}__"))
        return row

    def _is_allowed_label(self, split_item: DatasetSplitItem, config: TabularFeatureTrainingConfig) -> bool:
        if split_item.ground_truth_label is None:
            raise ValueError(f"dataset_split_item '{split_item.id}' has no ground_truth_label")
        if split_item.ground_truth_label == PredictedLabel.INCONCLUSIVE and not config.allow_inconclusive:
            return False
        return True

    def _as_array(self, rows: list[list[float]], feature_names: list[str]) -> np.ndarray:
        if not rows:
            return np.empty((0, len(feature_names)), dtype=float)
        return np.asarray(rows, dtype=float)


def _selected_modalities(config: TabularFeatureTrainingConfig) -> list[ImageModality]:
    if config.fusion_strategy == "petri_only":
        return [ImageModality.PETRI]
    if config.fusion_strategy == "micro_only":
        return [ImageModality.MICRO]
    modalities = []
    if config.use_petri_features:
        modalities.append(ImageModality.PETRI)
    if config.use_micro_features:
        modalities.append(ImageModality.MICRO)
    return [modality for modality in _MODALITY_ORDER if modality in modalities]


def _flatten_features(value: object, *, prefix: str) -> dict[str, float]:
    flattened: dict[str, float] = {}

    def visit(current: object, path: list[str]) -> None:
        if isinstance(current, bool) or current is None:
            return
        if isinstance(current, (int, float)):
            flattened["__".join([prefix.rstrip("__"), *path])] = float(current)
            return
        if isinstance(current, dict):
            for key in sorted(current):
                visit(current[key], [*path, str(key)])
            return
        if isinstance(current, list) and current and all(
            isinstance(item, (int, float)) and not isinstance(item, bool) for item in current
        ):
            if len(current) <= 64:
                for index, item in enumerate(current):
                    flattened["__".join([prefix.rstrip("__"), *path, f"{index:02d}"])] = float(item)

    visit(value, [])
    return flattened
