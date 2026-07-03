from __future__ import annotations

import os
from typing import Optional

import numpy as np
from PIL import Image, UnidentifiedImageError

from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.ml.configs.image_feature_extraction_config import ImageFeatureExtractionConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest, TrainingManifestItem
from blueberry_microid.ml.reports.image_feature_extraction_report import (
    FeatureVectorResult,
    ImageFeatureExtractionItemError,
    ImageFeatureExtractionReport,
)

EXTRACTION_VERSION = "v1"

_DARK_THRESHOLD = 64.0
_BRIGHT_THRESHOLD = 192.0
_EDGE_THRESHOLD = 20.0


class ImageFeatureExtractor:
    """Computes simple, reproducible, non-deep technical features from the
    Petri/micro image files referenced by a DatasetRelease's TrainingManifest.

    Uses only Pillow + numpy for lightweight statistical/edge computations —
    never PyTorch, TensorFlow, OpenCV, tensors, or a trained model. Every
    image is opened read-only; nothing here writes back to the original
    file. Every image in the manifest is always attempted (a failure never
    short-circuits the rest) — `fail_on_unreadable_image` only controls how
    the aggregate run status is classified afterward (see `extract`).
    """

    def extract(
        self, manifest: TrainingManifest, config: ImageFeatureExtractionConfig
    ) -> ImageFeatureExtractionReport:
        vectors: list[FeatureVectorResult] = []
        errors: list[ImageFeatureExtractionItemError] = []
        failed_item_ids: set[str] = set()
        processed_item_ids: set[str] = set()

        for item in manifest.items:
            for modality, path in (
                (ImageModality.PETRI, item.petri_image_path),
                (ImageModality.MICRO, item.micro_image_path),
            ):
                vector, error = self._extract_one(item, modality, path, config)
                if error is not None:
                    errors.append(error)
                    failed_item_ids.add(item.dataset_item_id)
                else:
                    assert vector is not None
                    vectors.append(vector)
                    processed_item_ids.add(item.dataset_item_id)

        petri_count = sum(1 for v in vectors if v.modality == ImageModality.PETRI)
        micro_count = sum(1 for v in vectors if v.modality == ImageModality.MICRO)
        status = _status_for(bool(errors), config.fail_on_unreadable_image)
        is_completed = status != ImageFeatureExtractionStatus.FAILED

        summary = {
            "error_count": len(errors),
            "errors": [
                {
                    "dataset_item_id": error.dataset_item_id,
                    "modality": error.modality.value,
                    "image_path": error.image_path,
                    "message": error.message,
                }
                for error in errors
            ],
            "contains_model_metrics": False,
            "contains_taxonomy": False,
            "extraction_version": EXTRACTION_VERSION,
        }

        return ImageFeatureExtractionReport(
            status=status,
            is_completed=is_completed,
            vectors=vectors,
            errors=errors,
            total_items=len(manifest.items),
            processed_items=len(processed_item_ids),
            failed_items=len(failed_item_ids),
            petri_feature_count=petri_count,
            micro_feature_count=micro_count,
            summary=summary,
        )

    def _extract_one(
        self,
        item: TrainingManifestItem,
        modality: ImageModality,
        path: str,
        config: ImageFeatureExtractionConfig,
    ) -> tuple[Optional[FeatureVectorResult], Optional[ImageFeatureExtractionItemError]]:
        def _error(message: str, error_path: Optional[str] = path) -> tuple[None, ImageFeatureExtractionItemError]:
            return None, ImageFeatureExtractionItemError(
                dataset_item_id=item.dataset_item_id,
                dataset_split_item_id=item.dataset_split_item_id,
                modality=modality,
                image_path=error_path,
                message=message,
            )

        if not path or not path.strip():
            return _error(f"{modality.value} image path is empty", None)
        if not os.path.exists(path):
            return _error(f"{modality.value} image file does not exist: {path}")

        try:
            with Image.open(path) as probe:
                probe.verify()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            return _error(f"{modality.value} image is not a valid or is a corrupted image: {exc}")

        try:
            with Image.open(path) as image:
                original_mode = image.mode
                original_width, original_height = image.size
                if (
                    config.max_image_pixels is not None
                    and original_width * original_height > config.max_image_pixels
                ):
                    return _error(f"{modality.value} image exceeds max_image_pixels")

                working = image.convert("RGB") if config.convert_to_rgb else image.copy()
                if config.resize_enabled:
                    working = working.resize((config.resize_width, config.resize_height))

                features = self._compute_features(working, config, real_file_size=os.path.getsize(path))
                processed_width, processed_height = working.size
                preprocessing = {
                    "convert_to_rgb": config.convert_to_rgb,
                    "resize_applied": config.resize_enabled,
                    "resize_width": config.resize_width if config.resize_enabled else None,
                    "resize_height": config.resize_height if config.resize_enabled else None,
                    "original_mode": original_mode,
                    "processed_mode": working.mode,
                    "original_width": original_width,
                    "original_height": original_height,
                    "processed_width": processed_width,
                    "processed_height": processed_height,
                }
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            return _error(f"{modality.value} image could not be processed: {exc}")

        vector = FeatureVectorResult(
            dataset_item_id=item.dataset_item_id,
            dataset_split_item_id=item.dataset_split_item_id,
            split=item.split,
            modality=modality,
            image_path=path,
            features=features,
            preprocessing=preprocessing,
        )
        return vector, None

    def _compute_features(
        self, image: Image.Image, config: ImageFeatureExtractionConfig, real_file_size: int
    ) -> dict:
        features: dict = {}

        if config.compute_basic_geometry:
            width, height = image.size
            features["geometry"] = {
                "width": width,
                "height": height,
                "aspect_ratio": round(width / height, 6) if height else None,
                "file_size_bytes": real_file_size,
            }

        gray = np.asarray(image.convert("L"), dtype=np.float64)

        if config.compute_intensity_features:
            features["intensity"] = {
                "mean_intensity": round(float(np.mean(gray)), 6),
                "std_intensity": round(float(np.std(gray)), 6),
                "min_intensity": float(np.min(gray)),
                "max_intensity": float(np.max(gray)),
            }

        if config.compute_color_features and image.mode in ("RGB", "RGBA"):
            rgb_image = image.convert("RGB")
            rgb = np.asarray(rgb_image, dtype=np.float64)
            red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
            hsv = np.asarray(rgb_image.convert("HSV"), dtype=np.float64)
            saturation = hsv[..., 1] / 255.0
            features["color"] = {
                "mean_r": round(float(np.mean(red)), 6),
                "mean_g": round(float(np.mean(green)), 6),
                "mean_b": round(float(np.mean(blue)), 6),
                "std_r": round(float(np.std(red)), 6),
                "std_g": round(float(np.std(green)), 6),
                "std_b": round(float(np.std(blue)), 6),
                "mean_saturation": round(float(np.mean(saturation)), 6),
            }

        if config.compute_sharpness_features:
            # A simple finite-differences discrete Laplacian (no OpenCV):
            # each pixel minus the average of its 4-neighbors, via np.roll.
            # np.roll wraps at the image border rather than padding — a
            # deliberate, documented simplification for this "aproximada"
            # metric, not a correctness bug.
            laplacian = (
                -4 * gray
                + np.roll(gray, 1, axis=0)
                + np.roll(gray, -1, axis=0)
                + np.roll(gray, 1, axis=1)
                + np.roll(gray, -1, axis=1)
            )
            features["sharpness"] = {"laplacian_variance": round(float(np.var(laplacian)), 6)}

        if config.compute_texture_features:
            dx = np.abs(np.diff(gray, axis=1))
            dy = np.abs(np.diff(gray, axis=0))
            edge_pixels = int(np.sum(dx > _EDGE_THRESHOLD)) + int(np.sum(dy > _EDGE_THRESHOLD))
            total_gradient_samples = dx.size + dy.size
            features["texture"] = {
                "edge_density": round(edge_pixels / total_gradient_samples, 6) if total_gradient_samples else 0.0,
                "dark_pixel_ratio": round(float(np.mean(gray < _DARK_THRESHOLD)), 6),
                "bright_pixel_ratio": round(float(np.mean(gray > _BRIGHT_THRESHOLD)), 6),
            }

        if config.compute_histogram_features:
            histogram, _ = np.histogram(gray, bins=config.histogram_bins, range=(0, 255))
            total = histogram.sum()
            normalized = (histogram / total).tolist() if total > 0 else [0.0] * config.histogram_bins
            features["histogram"] = {
                "grayscale_histogram": [round(value, 6) for value in normalized],
                "bins": config.histogram_bins,
            }

        return features


def _status_for(has_errors: bool, fail_on_unreadable_image: bool) -> ImageFeatureExtractionStatus:
    if not has_errors:
        return ImageFeatureExtractionStatus.COMPLETED
    return ImageFeatureExtractionStatus.FAILED if fail_on_unreadable_image else ImageFeatureExtractionStatus.PARTIAL
