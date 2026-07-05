"""Petri dish visual signal extractor for preliminary analysis.

Uses Pillow + OpenCV (opencv-python-headless, classical only) to compute
geometric and intensity signals from raw Petri dish image bytes.

No deep learning, no YOLO, no diagnostic labels, no taxonomy.
Candidate regions are geometric approximations; they are not confirmed
colonies and must not be presented as microbiological findings.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("blueberry_microid.ml.petri_visual_signal_extractor")

# Thresholds — tunable without changing business logic.
_MIN_REGION_AREA_FRACTION = 0.0005   # 0.05 % of total pixels
_MAX_REGION_AREA_FRACTION = 0.60     # 60 % — excludes agar background floods
_GAUSSIAN_KERNEL = (7, 7)
_MORPH_KERNEL_SIZE = (5, 5)
_LOW_SHARPNESS_THRESHOLD = 50.0
_OVEREXPOSED_MEAN = 230.0
_UNDEREXPOSED_MEAN = 25.0


@dataclass(frozen=True, slots=True)
class PetriVisualSignals:
    """Geometric/intensity signals extracted from a Petri dish photograph."""

    region_count: int
    colony_coverage: float      # fraction of total image area occupied by candidate regions (0–1)
    mean_saturation: float      # mean HSV-S of candidate region pixels, normalised 0–1
    mean_intensity: float       # overall grayscale mean (0–255)
    sharpness: float            # Laplacian variance (higher = sharper)
    extraction_ok: bool
    warnings: tuple[str, ...] = ()


class PetriVisualSignalExtractor:
    """Extract visual signals from Petri dish image bytes.

    Classical OpenCV pipeline: grayscale → Gaussian blur → Otsu threshold →
    morphological cleanup → contour detection → per-region metrics.
    Does not open any external files; reads only the provided bytes.
    """

    def extract(self, image_bytes: bytes) -> PetriVisualSignals:
        warnings: list[str] = []
        try:
            return self._extract_signals(image_bytes, warnings)
        except (UnidentifiedImageError, OSError, cv2.error, ValueError, Exception) as exc:
            logger.warning("petri_signal_extraction_failed exc_type=%s", type(exc).__name__)
            warnings.append(f"Petri image signal extraction failed: {type(exc).__name__}.")
            return PetriVisualSignals(
                region_count=0,
                colony_coverage=0.0,
                mean_saturation=0.0,
                mean_intensity=128.0,
                sharpness=0.0,
                extraction_ok=False,
                warnings=tuple(warnings),
            )

    def _extract_signals(self, image_bytes: bytes, warnings: list[str]) -> PetriVisualSignals:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            rgb = np.array(pil_img.convert("RGB"))

        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        total_pixels = int(gray.size)
        mean_intensity = float(gray.mean())

        if mean_intensity > _OVEREXPOSED_MEAN:
            warnings.append("Petri image may be overexposed (very high mean intensity).")
        if mean_intensity < _UNDEREXPOSED_MEAN:
            warnings.append("Petri image may be underexposed (very low mean intensity).")

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian.var())
        if sharpness < _LOW_SHARPNESS_THRESHOLD:
            warnings.append("Petri image appears blurry (low Laplacian variance).")

        blurred = cv2.GaussianBlur(gray, _GAUSSIAN_KERNEL, 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, _MORPH_KERNEL_SIZE)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = max(4, int(total_pixels * _MIN_REGION_AREA_FRACTION))
        max_area = int(total_pixels * _MAX_REGION_AREA_FRACTION)
        valid = [c for c in contours if min_area <= cv2.contourArea(c) <= max_area]
        region_count = len(valid)

        colony_mask = np.zeros(gray.shape, dtype=np.uint8)
        for c in valid:
            cv2.fillPoly(colony_mask, [c], 255)

        colony_pixels = int((colony_mask > 0).sum())
        colony_coverage = float(colony_pixels) / float(total_pixels)

        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        sat_channel = hsv[:, :, 1]  # S in [0, 255]
        if colony_pixels > 0:
            mean_saturation = float(sat_channel[colony_mask > 0].mean()) / 255.0
        else:
            mean_saturation = 0.0

        return PetriVisualSignals(
            region_count=region_count,
            colony_coverage=colony_coverage,
            mean_saturation=mean_saturation,
            mean_intensity=mean_intensity,
            sharpness=sharpness,
            extraction_ok=True,
            warnings=tuple(warnings),
        )
