from __future__ import annotations

from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.contracts.training_result import TrainingRunResult
from blueberry_microid.ml.reports.validation_report import ManifestValidationReport
from blueberry_microid.ml.validation.manifest_validator import ManifestValidator


class TrainingNotImplementedError(RuntimeError):
    """Raised when real training is invoked before its approved phase."""


class TrainerPort:
    """Future trainer contract. Real training is intentionally not implemented."""

    def __init__(self, validator: ManifestValidator | None = None) -> None:
        self._validator = validator or ManifestValidator()

    def validate_before_training(
        self,
        manifest: TrainingManifest,
        config: TrainingConfig,
    ) -> ManifestValidationReport:
        return self._validator.validate(manifest, config)

    def train(self, manifest: TrainingManifest, config: TrainingConfig) -> TrainingRunResult:
        raise TrainingNotImplementedError(
            "real model training is not implemented in this phase; validate the manifest only"
        )

