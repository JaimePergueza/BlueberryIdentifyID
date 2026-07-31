"""Explainable Petri-dish morphology signals for preliminary analysis.

The extractor isolates the plate when possible, excludes the outer rim and
uses classical colour, contrast and contour measurements. Candidate regions
remain visual approximations: they are not confirmed colonies and do not carry
any taxonomic or diagnostic meaning.
"""

from __future__ import annotations

import io
import logging
import math
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("blueberry_microid.ml.petri_visual_signal_extractor")

_MIN_REGION_AREA_FRACTION = 0.0005
_MAX_REGION_AREA_FRACTION = 0.45
_LOW_SHARPNESS_THRESHOLD = 50.0
_OVEREXPOSED_MEAN = 230.0
_UNDEREXPOSED_MEAN = 25.0
_MAX_PROCESSING_DIMENSION = 1200


@dataclass(frozen=True, slots=True)
class PetriVisualSignals:
    """Morphological and quality signals from a Petri-dish photograph."""

    region_count: int
    colony_coverage: float
    mean_saturation: float
    mean_intensity: float
    sharpness: float
    extraction_ok: bool
    plate_detected: bool = False
    plate_area_fraction: float = 1.0
    mean_region_area_fraction: float = 0.0
    mean_circularity: float = 0.0
    edge_irregularity: float = 0.0
    mean_texture_std: float = 0.0
    mean_hue: float = 0.0
    warnings: tuple[str, ...] = ()


class PetriVisualSignalExtractor:
    """Extract plate-aware classical morphology signals from image bytes."""

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

        rgb = _resize_for_processing(rgb)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        plate_mask, plate_detected = _detect_plate_mask(gray)
        plate_pixels = int(np.count_nonzero(plate_mask))
        total_pixels = int(gray.size)
        if plate_pixels == 0:
            raise ValueError("empty plate mask")

        if not plate_detected:
            warnings.append(
                "The Petri plate boundary could not be isolated reliably; the full image was analysed."
            )

        plate_values = gray[plate_mask > 0]
        mean_intensity = float(plate_values.mean())
        if mean_intensity > _OVEREXPOSED_MEAN:
            warnings.append("Petri image may be overexposed (very high mean intensity).")
        if mean_intensity < _UNDEREXPOSED_MEAN:
            warnings.append("Petri image may be underexposed (very low mean intensity).")

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian[plate_mask > 0].var())
        if sharpness < _LOW_SHARPNESS_THRESHOLD:
            warnings.append("Petri image appears blurry (low Laplacian variance).")

        interior_mask = _erode_plate_mask(plate_mask)
        interior_pixels = int(np.count_nonzero(interior_mask))
        if interior_pixels == 0:
            interior_mask = plate_mask.copy()
            interior_pixels = plate_pixels

        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        interior = interior_mask > 0

        local_background = cv2.GaussianBlur(gray, (0, 0), sigmaX=15.0)
        local_difference = cv2.absdiff(gray, local_background)
        median_intensity = float(np.median(gray[interior]))
        intensity_deviation = np.abs(gray.astype(np.float32) - median_intensity)

        median_lab = np.median(lab[interior], axis=0)
        colour_distance = np.linalg.norm(lab - median_lab, axis=2)

        local_threshold = max(6.0, float(np.percentile(local_difference[interior], 82)))
        colour_threshold = max(10.0, float(np.percentile(colour_distance[interior], 82)))
        intensity_threshold = max(12.0, min(38.0, float(gray[interior].std()) * 0.55))

        candidate = (
            (local_difference.astype(np.float32) >= local_threshold)
            | (colour_distance >= colour_threshold)
            | (intensity_deviation >= intensity_threshold)
        ) & interior

        candidate_mask = np.where(candidate, 255, 0).astype(np.uint8)
        scale = max(3, int(round(min(gray.shape) * 0.006)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (scale, scale))
        candidate_mask = cv2.morphologyEx(candidate_mask, cv2.MORPH_CLOSE, kernel)
        candidate_mask = cv2.morphologyEx(candidate_mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(candidate_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = max(8, int(interior_pixels * _MIN_REGION_AREA_FRACTION))
        max_area = int(interior_pixels * _MAX_REGION_AREA_FRACTION)
        valid = [c for c in contours if min_area <= cv2.contourArea(c) <= max_area]

        colony_mask = np.zeros(gray.shape, dtype=np.uint8)
        areas: list[float] = []
        circularities: list[float] = []
        irregularities: list[float] = []
        textures: list[float] = []
        hues: list[float] = []

        for contour in valid:
            area = float(cv2.contourArea(contour))
            perimeter = float(cv2.arcLength(contour, True))
            circularity = 0.0 if perimeter <= 0 else min(1.0, 4.0 * math.pi * area / (perimeter * perimeter))
            region_mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.fillPoly(region_mask, [contour], 255)
            region = region_mask > 0

            areas.append(area / float(interior_pixels))
            circularities.append(circularity)
            irregularities.append(1.0 - circularity)
            textures.append(float(gray[region].std()) if np.any(region) else 0.0)
            hues.append(float(hsv[:, :, 0][region].mean()) / 179.0 if np.any(region) else 0.0)
            cv2.fillPoly(colony_mask, [contour], 255)

        colony_pixels = int(np.count_nonzero((colony_mask > 0) & interior))
        colony_coverage = float(colony_pixels) / float(interior_pixels)
        saturation = hsv[:, :, 1]
        mean_saturation = (
            float(saturation[colony_mask > 0].mean()) / 255.0 if colony_pixels > 0 else 0.0
        )

        if len(valid) > 250:
            warnings.append(
                "A very high number of candidate regions was detected; debris or plate texture may be influencing the result."
            )

        return PetriVisualSignals(
            region_count=len(valid),
            colony_coverage=colony_coverage,
            mean_saturation=mean_saturation,
            mean_intensity=mean_intensity,
            sharpness=sharpness,
            extraction_ok=True,
            plate_detected=plate_detected,
            plate_area_fraction=float(plate_pixels) / float(total_pixels),
            mean_region_area_fraction=float(np.mean(areas)) if areas else 0.0,
            mean_circularity=float(np.mean(circularities)) if circularities else 0.0,
            edge_irregularity=float(np.mean(irregularities)) if irregularities else 0.0,
            mean_texture_std=float(np.mean(textures)) if textures else 0.0,
            mean_hue=float(np.mean(hues)) if hues else 0.0,
            warnings=tuple(warnings),
        )


def _resize_for_processing(rgb: np.ndarray) -> np.ndarray:
    height, width = rgb.shape[:2]
    longest = max(height, width)
    if longest <= _MAX_PROCESSING_DIMENSION:
        return rgb
    scale = _MAX_PROCESSING_DIMENSION / float(longest)
    return cv2.resize(
        rgb,
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        interpolation=cv2.INTER_AREA,
    )


def _detect_plate_mask(gray: np.ndarray) -> tuple[np.ndarray, bool]:
    height, width = gray.shape
    total = float(gray.size)
    threshold_value = max(12, int(np.percentile(gray, 8)))
    _, foreground = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    kernel_size = max(5, int(round(min(height, width) * 0.025)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centre = (width / 2.0, height / 2.0)
    candidates = [
        contour
        for contour in contours
        if cv2.contourArea(contour) >= total * 0.22
        and cv2.pointPolygonTest(contour, centre, False) >= 0
    ]
    if not candidates:
        return np.full(gray.shape, 255, dtype=np.uint8), False

    contour = max(candidates, key=cv2.contourArea)
    area_fraction = float(cv2.contourArea(contour)) / total
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [contour], 255)
    detected = area_fraction < 0.94
    return mask, detected


def _erode_plate_mask(mask: np.ndarray) -> np.ndarray:
    kernel_size = max(3, int(round(min(mask.shape) * 0.035)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    return cv2.erode(mask, kernel, iterations=1)
