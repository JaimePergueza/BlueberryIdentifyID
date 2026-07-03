from __future__ import annotations

from pathlib import Path

from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.reports.validation_report import ManifestValidationReport


class ImagePathValidator:
    """Checks image path existence without opening or copying image bytes."""

    def validate(self, manifest: TrainingManifest) -> ManifestValidationReport:
        errors: list[str] = []
        for index, item in enumerate(manifest.items):
            if item.petri_image_path and not Path(item.petri_image_path).exists():
                errors.append(f"item[{index}] petri_image_path does not exist: {item.petri_image_path}")
            if item.micro_image_path and not Path(item.micro_image_path).exists():
                errors.append(f"item[{index}] micro_image_path does not exist: {item.micro_image_path}")
        return ManifestValidationReport(
            is_valid=not errors,
            errors=errors,
            item_count=len(manifest.items),
            recommendations=["image paths exist" if not errors else "fix missing image paths before training"],
        )

