from __future__ import annotations

import json
from pathlib import Path

from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest, TrainingManifestItem
from blueberry_microid.ml.data.dataset_loader import DatasetLoaderPort
from blueberry_microid.ml.reports.validation_report import ManifestValidationReport
from blueberry_microid.ml.validation.manifest_validator import ManifestValidator


class JsonManifestDatasetLoader(DatasetLoaderPort):
    """Loads DatasetRelease manifests from JSON. It never loads image bytes."""

    def __init__(self, validator: ManifestValidator | None = None) -> None:
        self._validator = validator or ManifestValidator()
        self._manifest: TrainingManifest | None = None

    def load_manifest(self, path: str | Path) -> TrainingManifest:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self._manifest = TrainingManifest.from_dict(payload)
        return self._manifest

    def validate_manifest(self, manifest: TrainingManifest, config: TrainingConfig) -> ManifestValidationReport:
        return self._validator.validate(manifest, config)

    def iter_items(self, split: str) -> list[TrainingManifestItem]:
        if self._manifest is None:
            raise RuntimeError("manifest must be loaded before iterating items")
        return [item for item in self._manifest.items if item.split == split]

