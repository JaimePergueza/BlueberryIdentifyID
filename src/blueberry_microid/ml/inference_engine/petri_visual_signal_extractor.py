"""Explainable Petri-dish morphology signals for preliminary analysis.

The extractor isolates the plate when possible, excludes the outer rim and
uses classical colour, contrast, texture and contour measurements. Candidate
regions remain visual approximations: they are not confirmed colonies and do
not carry taxonomic or diagnostic meaning.
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
_MAX_CONFLUENT_AREA_FRACTION = 0.88
_LOW_SHARPNESS_THRESHOLD = 50.0
_OVEREXPOSED_MEAN = 230.0
_UNDEREXPOSED_MEAN = 25.0
_MAX_PROCESSING_DIMENSION = 1200
_MAX_VISUAL_REGIONS = 80
_SEGMENTATION_CONFLICT_SIGNAL_FRACTION = 0.08
_SEGMENTATION_CONFLICT_STD = 14.0


@dataclass(frozen=True, slots=True)
class PetriVisualSignals:
    """Morphological, quality and visualisation signals from a Petri image."""

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
    candidate_signal_fraction: float = 0.0
    segmentation_conflict: bool = False
    confluent_growth_detected: bool = False
    visualization: dict | None = None
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
        height, width = rgb.shape[:2]
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        plate_mask, plate_detected, plate_outline = _detect_plate_mask(gray)
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
        interior = interior_mask > 0

        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        local_background = cv2.GaussianBlur(gray, (0, 0), sigmaX=15.0)
        local_difference = cv2.absdiff(gray, local_background)
        median_intensity = float(np.median(gray[interior]))
        intensity_deviation = np.abs(gray.astype(np.float32) - median_intensity)
        median_lab = np.median(lab[interior], axis=0)
        colour_distance = np.linalg.norm(lab - median_lab, axis=2)
        local_texture = _local_texture(gray)

        permissive_mask = _build_permissive_mask(
            local_difference=local_difference,
            colour_distance=colour_distance,
            intensity_deviation=intensity_deviation,
            interior=interior,
        )
        candidate_signal_fraction = float(np.count_nonzero(permissive_mask)) / float(
            interior_pixels
        )
        min_area = max(8, int(interior_pixels * _MIN_REGION_AREA_FRACTION))
        max_area = int(interior_pixels * _MAX_REGION_AREA_FRACTION)

        permissive_contours = _external_contours(permissive_mask)
        valid = [
            contour
            for contour in permissive_contours
            if min_area <= cv2.contourArea(contour) <= max_area
        ]
        oversized = [
            contour
            for contour in permissive_contours
            if max_area < cv2.contourArea(contour)
            <= interior_pixels * _MAX_CONFLUENT_AREA_FRACTION
        ]

        confluent_growth_detected = False
        unresolved_oversized = False
        if oversized or (not valid and candidate_signal_fraction >= 0.08):
            refined_mask = _build_conservative_mask(
                local_difference=local_difference,
                colour_distance=colour_distance,
                intensity_deviation=intensity_deviation,
                local_texture=local_texture,
                interior=interior,
            )
            refined_contours = _external_contours(refined_mask)
            refined_valid = [
                contour
                for contour in refined_contours
                if min_area <= cv2.contourArea(contour) <= max_area
            ]
            refined_oversized = [
                contour
                for contour in refined_contours
                if max_area < cv2.contourArea(contour)
                <= interior_pixels * _MAX_CONFLUENT_AREA_FRACTION
            ]

            split_regions: list[np.ndarray] = []
            for contour in refined_oversized:
                split_regions.extend(
                    _split_confluent_region(
                        rgb=rgb,
                        contour=contour,
                        interior_mask=interior_mask,
                        min_area=min_area,
                        max_area=max_area,
                    )
                )

            if refined_valid or split_regions:
                valid = refined_valid + split_regions
                confluent_growth_detected = bool(oversized or refined_oversized)
            elif oversized or refined_oversized:
                unresolved_oversized = True

        valid = _deduplicate_contours(valid)
        valid.sort(key=cv2.contourArea, reverse=True)

        interior_std = float(gray[interior].std())
        segmentation_conflict = bool(
            plate_detected
            and not valid
            and (
                unresolved_oversized
                or (
                    candidate_signal_fraction >= _SEGMENTATION_CONFLICT_SIGNAL_FRACTION
                    and interior_std >= _SEGMENTATION_CONFLICT_STD
                )
            )
        )
        if segmentation_conflict:
            warnings.append(
                "Petri growth-like contrast or texture was detected, but it could not be separated "
                "into reliable regions. The macroscopic result must be treated as inconclusive."
            )
        if confluent_growth_detected:
            warnings.append(
                "Large or connected growth was refined with conservative segmentation; region "
                "boundaries remain approximate."
            )

        colony_mask = np.zeros(gray.shape, dtype=np.uint8)
        areas: list[float] = []
        circularities: list[float] = []
        irregularities: list[float] = []
        textures: list[float] = []
        hues: list[float] = []
        visual_regions: list[dict] = []

        for index, contour in enumerate(valid):
            area = float(cv2.contourArea(contour))
            perimeter = float(cv2.arcLength(contour, True))
            circularity = (
                0.0
                if perimeter <= 0
                else min(1.0, 4.0 * math.pi * area / (perimeter * perimeter))
            )
            region_mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.fillPoly(region_mask, [contour], 255)
            region = (region_mask > 0) & interior
            if not np.any(region):
                continue

            area_fraction = area / float(interior_pixels)
            areas.append(area_fraction)
            circularities.append(circularity)
            irregularities.append(1.0 - circularity)
            textures.append(float(gray[region].std()))
            hues.append(float(hsv[:, :, 0][region].mean()) / 179.0)
            cv2.fillPoly(colony_mask, [contour], 255)

            if index < _MAX_VISUAL_REGIONS:
                x, y, box_width, box_height = cv2.boundingRect(contour)
                visual_regions.append(
                    {
                        "id": index + 1,
                        "role": "candidate_colony",
                        "bbox": _normalised_box(
                            x, y, box_width, box_height, width, height
                        ),
                        "polygon": _normalised_polygon(contour, width, height),
                        "area_fraction": round(area_fraction, 6),
                        "circularity": round(circularity, 4),
                    }
                )

        colony_pixels = int(np.count_nonzero((colony_mask > 0) & interior))
        colony_coverage = float(colony_pixels) / float(interior_pixels)
        saturation = hsv[:, :, 1]
        mean_saturation = (
            float(saturation[(colony_mask > 0) & interior].mean()) / 255.0
            if colony_pixels > 0
            else 0.0
        )

        if len(valid) > 250:
            warnings.append(
                "A very high number of candidate regions was detected; debris or plate texture "
                "may be influencing the result."
            )
        if len(valid) > _MAX_VISUAL_REGIONS:
            warnings.append(
                f"Only the {_MAX_VISUAL_REGIONS} largest candidate regions are shown in the "
                "visual overlay."
            )

        visualization = {
            "kind": "petri",
            "coordinate_space": "normalized",
            "image_width": width,
            "image_height": height,
            "outline": plate_outline,
            "regions": visual_regions,
            "branch_points": [],
        }

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
            candidate_signal_fraction=candidate_signal_fraction,
            segmentation_conflict=segmentation_conflict,
            confluent_growth_detected=confluent_growth_detected,
            visualization=visualization,
            warnings=tuple(warnings),
        )


def _build_permissive_mask(
    *,
    local_difference: np.ndarray,
    colour_distance: np.ndarray,
    intensity_deviation: np.ndarray,
    interior: np.ndarray,
) -> np.ndarray:
    local_threshold = max(6.0, float(np.percentile(local_difference[interior], 82)))
    colour_threshold = max(10.0, float(np.percentile(colour_distance[interior], 82)))
    intensity_threshold = max(
        12.0,
        min(
            38.0,
            float(np.std(intensity_deviation[interior])) * 0.85,
        ),
    )
    candidate = (
        (local_difference.astype(np.float32) >= local_threshold)
        | (colour_distance >= colour_threshold)
        | (intensity_deviation >= intensity_threshold)
    ) & interior

    mask = np.where(candidate, 255, 0).astype(np.uint8)
    scale = max(3, int(round(min(mask.shape) * 0.006)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (scale, scale))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


def _build_conservative_mask(
    *,
    local_difference: np.ndarray,
    colour_distance: np.ndarray,
    intensity_deviation: np.ndarray,
    local_texture: np.ndarray,
    interior: np.ndarray,
) -> np.ndarray:
    local_threshold = max(6.0, float(np.percentile(local_difference[interior], 70)))
    colour_threshold = max(10.0, float(np.percentile(colour_distance[interior], 70)))
    intensity_threshold = max(12.0, float(np.percentile(intensity_deviation[interior], 70)))
    texture_threshold = max(5.0, float(np.percentile(local_texture[interior], 70)))

    votes = (
        (local_difference.astype(np.float32) >= local_threshold).astype(np.uint8)
        + (colour_distance >= colour_threshold).astype(np.uint8)
        + (intensity_deviation >= intensity_threshold).astype(np.uint8)
        + (local_texture >= texture_threshold).astype(np.uint8)
    )
    candidate = (votes >= 3) & interior
    mask = np.where(candidate, 255, 0).astype(np.uint8)
    scale = max(3, int(round(min(mask.shape) * 0.004)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (scale, scale))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def _local_texture(gray: np.ndarray) -> np.ndarray:
    source = gray.astype(np.float32)
    local_mean = cv2.GaussianBlur(source, (0, 0), sigmaX=5.0)
    local_square_mean = cv2.GaussianBlur(source * source, (0, 0), sigmaX=5.0)
    variance = np.maximum(0.0, local_square_mean - local_mean * local_mean)
    return np.sqrt(variance)


def _split_confluent_region(
    *,
    rgb: np.ndarray,
    contour: np.ndarray,
    interior_mask: np.ndarray,
    min_area: int,
    max_area: int,
) -> list[np.ndarray]:
    region_mask = np.zeros(interior_mask.shape, dtype=np.uint8)
    cv2.fillPoly(region_mask, [contour], 255)
    region_mask = cv2.bitwise_and(region_mask, interior_mask)
    distance = cv2.distanceTransform(region_mask, cv2.DIST_L2, 5)
    maximum = float(distance.max())
    if maximum <= 0:
        return []

    sure_foreground = np.where(distance >= maximum * 0.30, 255, 0).astype(np.uint8)
    marker_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    sure_foreground = cv2.morphologyEx(
        sure_foreground, cv2.MORPH_OPEN, marker_kernel
    )
    marker_count, markers = cv2.connectedComponents(sure_foreground)
    if marker_count <= 2:
        return []

    sure_background = cv2.dilate(region_mask, marker_kernel, iterations=2)
    unknown = cv2.subtract(sure_background, sure_foreground)
    markers = markers + 1
    markers[unknown > 0] = 0
    watershed_input = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR).copy()
    cv2.watershed(watershed_input, markers)

    regions: list[np.ndarray] = []
    for marker in range(2, int(markers.max()) + 1):
        segment = np.where(markers == marker, 255, 0).astype(np.uint8)
        segment = cv2.bitwise_and(segment, interior_mask)
        contours = _external_contours(segment)
        if not contours:
            continue
        piece = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(piece))
        if min_area <= area <= max_area:
            regions.append(piece)
    return regions


def _external_contours(mask: np.ndarray) -> list[np.ndarray]:
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return list(contours)


def _deduplicate_contours(contours: list[np.ndarray]) -> list[np.ndarray]:
    ordered = sorted(contours, key=cv2.contourArea, reverse=True)
    accepted: list[np.ndarray] = []
    for contour in ordered:
        x, y, width, height = cv2.boundingRect(contour)
        candidate_box = (x, y, width, height)
        if any(
            _box_containment(candidate_box, cv2.boundingRect(other)) >= 0.85
            for other in accepted
        ):
            continue
        accepted.append(contour)
    return accepted


def _box_containment(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    x1, y1, w1, h1 = first
    x2, y2, w2, h2 = second
    left = max(x1, x2)
    top = max(y1, y2)
    right = min(x1 + w1, x2 + w2)
    bottom = min(y1 + h1, y2 + h2)
    intersection = max(0, right - left) * max(0, bottom - top)
    smaller = max(1, min(w1 * h1, w2 * h2))
    return intersection / float(smaller)


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


def _detect_plate_mask(gray: np.ndarray) -> tuple[np.ndarray, bool, dict | None]:
    circle = _detect_central_circle(gray)
    if circle is not None:
        centre_x, centre_y, radius = circle
        mask = np.zeros(gray.shape, dtype=np.uint8)
        safe_radius = max(1, int(round(radius * 0.985)))
        cv2.circle(mask, (centre_x, centre_y), safe_radius, 255, thickness=-1)
        return mask, True, _normalised_ellipse(
            centre_x, centre_y, safe_radius, safe_radius, gray
        )

    height, width = gray.shape
    total = float(gray.size)
    threshold_value = max(12, int(np.percentile(gray, 8)))
    _, foreground = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    kernel_size = max(5, int(round(min(height, width) * 0.025)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    centre = (width / 2.0, height / 2.0)
    candidates = [
        contour
        for contour in contours
        if cv2.contourArea(contour) >= total * 0.18
        and cv2.pointPolygonTest(contour, centre, False) >= 0
    ]
    if not candidates:
        return np.full(gray.shape, 255, dtype=np.uint8), False, None

    contour = max(candidates, key=cv2.contourArea)
    area_fraction = float(cv2.contourArea(contour)) / total
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [contour], 255)
    detected = 0.18 <= area_fraction <= 0.985
    outline = (
        {
            "type": "polygon",
            "points": _normalised_polygon(
                contour, width, height, epsilon_ratio=0.01
            ),
        }
        if detected
        else None
    )
    return mask, detected, outline


def _detect_central_circle(gray: np.ndarray) -> tuple[int, int, int] | None:
    height, width = gray.shape
    minimum = min(height, width)
    blurred = cv2.GaussianBlur(gray, (9, 9), 1.8)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(20, int(minimum * 0.45)),
        param1=110,
        param2=32,
        minRadius=max(8, int(minimum * 0.25)),
        maxRadius=max(12, int(minimum * 0.56)),
    )
    if circles is None:
        return None

    image_centre = np.array([width / 2.0, height / 2.0], dtype=np.float64)
    candidates: list[tuple[float, int, int, int]] = []
    for x_value, y_value, radius_value in np.round(circles[0]).astype(int):
        if radius_value <= 0:
            continue
        centre_distance = float(
            np.linalg.norm(np.array([x_value, y_value]) - image_centre)
        )
        if centre_distance > minimum * 0.22:
            continue
        radius_fraction = radius_value / float(minimum)
        if not 0.25 <= radius_fraction <= 0.56:
            continue
        score = centre_distance / float(minimum) + abs(radius_fraction - 0.46)
        candidates.append((score, x_value, y_value, radius_value))

    if not candidates:
        return None
    _, x_value, y_value, radius_value = min(candidates, key=lambda item: item[0])
    return int(x_value), int(y_value), int(radius_value)


def _erode_plate_mask(mask: np.ndarray) -> np.ndarray:
    kernel_size = max(3, int(round(min(mask.shape) * 0.035)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    return cv2.erode(mask, kernel, iterations=1)


def _normalised_box(
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
) -> dict:
    return {
        "x": round(x / float(image_width), 6),
        "y": round(y / float(image_height), 6),
        "width": round(width / float(image_width), 6),
        "height": round(height / float(image_height), 6),
    }


def _normalised_polygon(
    contour: np.ndarray,
    width: int,
    height: int,
    *,
    epsilon_ratio: float = 0.025,
) -> list[dict]:
    perimeter = max(1.0, float(cv2.arcLength(contour, True)))
    simplified = cv2.approxPolyDP(contour, perimeter * epsilon_ratio, True)
    points: list[dict] = []
    for point in simplified.reshape(-1, 2)[:40]:
        points.append(
            {
                "x": round(float(point[0]) / float(width), 6),
                "y": round(float(point[1]) / float(height), 6),
            }
        )
    return points


def _normalised_ellipse(
    centre_x: int,
    centre_y: int,
    radius_x: int,
    radius_y: int,
    image: np.ndarray,
) -> dict:
    height, width = image.shape[:2]
    return {
        "type": "ellipse",
        "cx": round(centre_x / float(width), 6),
        "cy": round(centre_y / float(height), 6),
        "rx": round(radius_x / float(width), 6),
        "ry": round(radius_y / float(height), 6),
    }
