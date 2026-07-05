"""Microscopy image visual signal extractor for preliminary analysis.

Uses Pillow + numpy to compute intensity and texture signals from raw
microscopy image bytes.  No OpenCV, no deep learning, no diagnostic labels.

The signals produced are statistical summaries of pixel values only.
They cannot identify microorganism species or genus.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("blueberry_microid.ml.micro_visual_signal_extractor")

# Thresholds aligned with ImageFeatureExtractor constants where possible.
_EDGE_GRADIENT_THRESHOLD = 20.0    # same as _EDGE_THRESHOLD in image_feature_extractor.py
_LOW_SHARPNESS_THRESHOLD = 30.0
_EMPTY_FIELD_STD_THRESHOLD = 10.0
_EMPTY_FIELD_EDGE_THRESHOLD = 0.02


@dataclass(frozen=True, slots=True)
class MicroVisualSignals:
    """Intensity and texture signals extracted from a microscopy photograph."""

    mean_intensity: float   # grayscale mean (0–255)
    intensity_std: float    # grayscale standard deviation
    sharpness: float        # Laplacian variance via finite differences (higher = sharper)
    edge_density: float     # fraction of pixels with gradient magnitude > threshold (0–1)
    extraction_ok: bool
    warnings: tuple[str, ...] = ()


class MicroVisualSignalExtractor:
    """Extract visual signals from microscopy image bytes using Pillow + numpy.

    Computes: mean intensity, std, Laplacian-based sharpness, and edge density
    via numpy gradient.  Does not open any external files; reads only bytes.
    """

    def extract(self, image_bytes: bytes) -> MicroVisualSignals:
        warnings: list[str] = []
        try:
            return self._extract_signals(image_bytes, warnings)
        except (UnidentifiedImageError, OSError, ValueError, Exception) as exc:
            logger.warning("micro_signal_extraction_failed exc_type=%s", type(exc).__name__)
            warnings.append(f"Micro image signal extraction failed: {type(exc).__name__}.")
            return MicroVisualSignals(
                mean_intensity=128.0,
                intensity_std=0.0,
                sharpness=0.0,
                edge_density=0.0,
                extraction_ok=False,
                warnings=tuple(warnings),
            )

    def _extract_signals(self, image_bytes: bytes, warnings: list[str]) -> MicroVisualSignals:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            arr = np.array(pil_img.convert("L"), dtype=np.float64)

        mean_intensity = float(arr.mean())
        intensity_std = float(arr.std())

        # Laplacian via finite differences (same pattern as ImageFeatureExtractor)
        laplacian = (
            np.roll(arr, 1, 0) + np.roll(arr, -1, 0)
            + np.roll(arr, 1, 1) + np.roll(arr, -1, 1)
            - 4.0 * arr
        )
        sharpness = float(laplacian.var())

        # Edge density via numpy gradient
        gy, gx = np.gradient(arr)
        edge_magnitude = np.hypot(gx, gy)
        edge_density = float((edge_magnitude > _EDGE_GRADIENT_THRESHOLD).mean())

        if sharpness < _LOW_SHARPNESS_THRESHOLD:
            warnings.append("Micro image appears blurry (low Laplacian variance).")
        if intensity_std < _EMPTY_FIELD_STD_THRESHOLD and edge_density < _EMPTY_FIELD_EDGE_THRESHOLD:
            warnings.append("Micro image appears nearly uniform — field of view may be empty or unfocused.")

        return MicroVisualSignals(
            mean_intensity=mean_intensity,
            intensity_std=intensity_std,
            sharpness=sharpness,
            edge_density=edge_density,
            extraction_ok=True,
            warnings=tuple(warnings),
        )
