from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest, TrainingManifestItem
from blueberry_microid.ml.reports.validation_report import ManifestValidationReport


class DatasetLoaderPort(ABC):
    @abstractmethod
    def load_manifest(self, path: str | Path) -> TrainingManifest:
        raise NotImplementedError

    @abstractmethod
    def validate_manifest(self, manifest: TrainingManifest, config: TrainingConfig) -> ManifestValidationReport:
        raise NotImplementedError

    @abstractmethod
    def iter_items(self, split: str) -> list[TrainingManifestItem]:
        raise NotImplementedError

