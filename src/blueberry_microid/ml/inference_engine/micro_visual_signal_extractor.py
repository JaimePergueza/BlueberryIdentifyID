"""Explainable microscopy morphology signals for preliminary analysis.

The extractor isolates the illuminated field of view when possible and uses
classical image processing to estimate filament coverage, skeleton branching,
component elongation and general texture. These metrics describe visible
structures only and cannot identify genus or species.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("blueberry_microid.ml.micro_visual_signal_extractor")

_EDGE_GRADIENT_THRESHOLD = 20.0
_LOW_SHARPNESS_THRESHOLD = 30.0
_EMPTY_FIELD_STD_THRESHOLD = 10.0
_EMPTY_FIELD_EDGE_THRESHOLD = 0.02
_MAX_PROCESSING_DIMENSION = 1200
_MAX_VISUAL_COMPONENTS = 100
_MAX_VISUAL_BRANCH_POINTS = 160


@dataclass(frozen=True, slots=True)
class MicroVisualSignals:
    """Texture, filament, quality and visualisation signals from microscopy."""

    mean_intensity: float
    intensity_std: float
    sharpness: float
    edge_density: float
    extraction_ok: bool
    field_detected: bool = False
    field_coverage: float = 1.0
    filament_coverage: float = 0.0
    skeleton_density: float = 0.0
    branch_point_density: float = 0.0
    elongated_component_ratio: float = 0.0
    round_component_density: float = 0.0
    component_count: int = 0
    visualization: dict | None = None
    warnings: tuple[str, ...] = ()


class MicroVisualSignalExtractor:
    """Extract field-aware classical morphology signals from microscopy bytes."""

    def extract(self, image_bytes: bytes) -> MicroVisualSignals:
        warnings: list[str] = []
        try:
            return self._extract_signals(image_bytes, warnings)
        except (UnidentifiedImageError, OSError, cv2.error, ValueError, Exception) as exc:
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
            rgb = np.array(pil_img.convert("RGB"))

        rgb = _resize_for_processing(rgb)
        height, width = rgb.shape[:2]
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        field_mask, field_detected, field_outline = _detect_field_mask(gray)
        field = field_mask > 0
        field_pixels = int(np.count_nonzero(field))
        if field_pixels == 0:
            raise ValueError("empty microscopy field mask")

        if not field_detected:
            warnings.append(
                "The illuminated microscopy field could not be isolated reliably; the full image was analysed."
            )

        field_values = gray[field].astype(np.float64)
        mean_intensity = float(field_values.mean())
        intensity_std = float(field_values.std())

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian[field].var())

        gy, gx = np.gradient(gray.astype(np.float64))
        edge_magnitude = np.hypot(gx, gy)
        edge_density = float(
            np.count_nonzero((edge_magnitude > _EDGE_GRADIENT_THRESHOLD) & field)
        ) / float(field_pixels)

        line_mask = _extract_dark_filament_mask(gray, field_mask)
        line_mask = _remove_implausible_components(line_mask, field_pixels)
        filament_pixels = int(np.count_nonzero(line_mask))
        filament_coverage = float(filament_pixels) / float(field_pixels)

        skeleton = _morphological_skeleton(line_mask)
        skeleton_pixels = int(np.count_nonzero(skeleton))
        skeleton_density = float(skeleton_pixels) / float(field_pixels)
        branch_point_density, branch_points = _branch_points(
            skeleton,
            field_pixels,
            width,
            height,
        )
        component_count, elongated_ratio, round_density, visual_components = _component_morphology(
            line_mask,
            field_pixels,
            width,
            height,
        )

        if sharpness < _LOW_SHARPNESS_THRESHOLD:
            warnings.append("Micro image appears blurry (low Laplacian variance).")
        if intensity_std < _EMPTY_FIELD_STD_THRESHOLD and edge_density < _EMPTY_FIELD_EDGE_THRESHOLD:
            warnings.append("Micro image appears nearly uniform — field of view may be empty or unfocused.")
        if filament_coverage > 0.35:
            warnings.append(
                "A large part of the microscopy field was segmented as structure; staining, debris or illumination may be influencing the measurement."
            )
        if component_count > _MAX_VISUAL_COMPONENTS:
            warnings.append(
                f"Only the {_MAX_VISUAL_COMPONENTS} largest microscopy components are shown in the visual overlay."
            )

        visualization = {
            "kind": "micro",
            "coordinate_space": "normalized",
            "image_width": width,
            "image_height": height,
            "outline": field_outline,
            "regions": visual_components,
            "branch_points": branch_points,
        }

        return MicroVisualSignals(
            mean_intensity=mean_intensity,
            intensity_std=intensity_std,
            sharpness=sharpness,
            edge_density=edge_density,
            extraction_ok=True,
            field_detected=field_detected,
            field_coverage=float(field_pixels) / float(gray.size),
            filament_coverage=filament_coverage,
            skeleton_density=skeleton_density,
            branch_point_density=branch_point_density,
            elongated_component_ratio=elongated_ratio,
            round_component_density=round_density,
            component_count=component_count,
            visualization=visualization,
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


def _detect_field_mask(gray: np.ndarray) -> tuple[np.ndarray, bool, dict | None]:
    circle = _detect_central_circle(gray)
    if circle is not None:
        centre_x, centre_y, radius = circle
        mask = np.zeros(gray.shape, dtype=np.uint8)
        safe_radius = max(1, int(round(radius * 0.985)))
        cv2.circle(mask, (centre_x, centre_y), safe_radius, 255, thickness=-1)
        return mask, True, _normalised_ellipse(centre_x, centre_y, safe_radius, safe_radius, gray)

    height, width = gray.shape
    total = float(gray.size)
    threshold = max(8, int(np.percentile(gray, 5)))
    _, illuminated = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    kernel_size = max(5, int(round(min(height, width) * 0.02)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    illuminated = cv2.morphologyEx(illuminated, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(illuminated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
    erosion_size = max(3, int(round(min(height, width) * 0.012)))
    erosion_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erosion_size, erosion_size))
    mask = cv2.erode(mask, erosion_kernel, iterations=1)
    detected = 0.18 <= area_fraction <= 0.985
    outline = {
        "type": "polygon",
        "points": _normalised_polygon(contour, width, height, epsilon_ratio=0.01),
    } if detected else None
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
        param1=100,
        param2=30,
        minRadius=max(8, int(minimum * 0.25)),
        maxRadius=max(12, int(minimum * 0.58)),
    )
    if circles is None:
        return None

    image_centre = np.array([width / 2.0, height / 2.0], dtype=np.float64)
    candidates: list[tuple[float, int, int, int]] = []
    for x_value, y_value, radius_value in np.round(circles[0]).astype(int):
        if radius_value <= 0:
            continue
        centre_distance = float(np.linalg.norm(np.array([x_value, y_value]) - image_centre))
        if centre_distance > minimum * 0.24:
            continue
        radius_fraction = radius_value / float(minimum)
        if not 0.25 <= radius_fraction <= 0.58:
            continue
        score = centre_distance / float(minimum) + abs(radius_fraction - 0.47)
        candidates.append((score, x_value, y_value, radius_value))

    if not candidates:
        return None
    _, x_value, y_value, radius_value = min(candidates, key=lambda item: item[0])
    return int(x_value), int(y_value), int(radius_value)


def _extract_dark_filament_mask(gray: np.ndarray, field_mask: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    background = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=9.0)
    dark_difference = cv2.subtract(background, enhanced)
    field = field_mask > 0
    threshold = max(7.0, float(np.percentile(dark_difference[field], 84)))
    candidate = (dark_difference.astype(np.float32) >= threshold) & field

    mask = np.where(candidate, 255, 0).astype(np.uint8)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), dtype=np.uint8))
    return mask


def _remove_implausible_components(mask: np.ndarray, field_pixels: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    cleaned = np.zeros(mask.shape, dtype=np.uint8)
    min_area = max(4, int(field_pixels * 0.00001))
    max_area = max(min_area + 1, int(field_pixels * 0.20))
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if min_area <= area <= max_area:
            cleaned[labels == label] = 255
    return cleaned


def _morphological_skeleton(mask: np.ndarray) -> np.ndarray:
    image = np.where(mask > 0, 255, 0).astype(np.uint8)
    skeleton = np.zeros_like(image)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    max_iterations = max(image.shape) * 2
    for _ in range(max_iterations):
        eroded = cv2.erode(image, element)
        opened = cv2.dilate(eroded, element)
        skeleton = cv2.bitwise_or(skeleton, cv2.subtract(image, opened))
        image = eroded
        if cv2.countNonZero(image) == 0:
            break
    return skeleton


def _branch_points(
    skeleton: np.ndarray,
    field_pixels: int,
    width: int,
    height: int,
) -> tuple[float, list[dict]]:
    binary = (skeleton > 0).astype(np.uint8)
    if not np.any(binary):
        return 0.0, []
    neighbours = cv2.filter2D(binary, cv2.CV_16S, np.ones((3, 3), dtype=np.uint8)) - binary
    branch_mask = (binary > 0) & (neighbours >= 3)
    coordinates = np.argwhere(branch_mask)
    density = float(len(coordinates)) / float(field_pixels)

    if len(coordinates) > _MAX_VISUAL_BRANCH_POINTS:
        step = max(1, len(coordinates) // _MAX_VISUAL_BRANCH_POINTS)
        coordinates = coordinates[::step][:_MAX_VISUAL_BRANCH_POINTS]

    points = [
        {
            "x": round(float(column) / float(width), 6),
            "y": round(float(row) / float(height), 6),
        }
        for row, column in coordinates
    ]
    return density, points


def _component_morphology(
    mask: np.ndarray,
    field_pixels: int,
    image_width: int,
    image_height: int,
) -> tuple[int, float, float, list[dict]]:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    component_count = max(0, count - 1)
    if component_count == 0:
        return 0, 0.0, 0.0, []

    elongated = 0
    roundish = 0
    components: list[dict] = []
    for label in range(1, count):
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        area = int(stats[label, cv2.CC_STAT_AREA])
        short = max(1, min(width, height))
        aspect = max(width, height) / float(short)
        fill_ratio = area / float(max(1, width * height))
        is_elongated = aspect >= 2.8
        if is_elongated:
            elongated += 1
        if aspect <= 1.6 and fill_ratio >= 0.35:
            roundish += 1
        components.append(
            {
                "id": label,
                "role": "filament_component" if is_elongated else "structure_component",
                "bbox": _normalised_box(x, y, width, height, image_width, image_height),
                "area_fraction": round(area / float(field_pixels), 7),
                "aspect_ratio": round(aspect, 3),
            }
        )

    components.sort(key=lambda item: item["area_fraction"], reverse=True)
    return (
        component_count,
        elongated / float(component_count),
        roundish / float(max(1, field_pixels)),
        components[:_MAX_VISUAL_COMPONENTS],
    )


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
    return [
        {
            "x": round(float(point[0]) / float(width), 6),
            "y": round(float(point[1]) / float(height), 6),
        }
        for point in simplified.reshape(-1, 2)[:40]
    ]


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
