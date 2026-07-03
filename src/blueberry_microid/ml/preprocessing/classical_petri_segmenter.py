from __future__ import annotations

import os
from typing import Optional

import cv2
import numpy as np

from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus
from blueberry_microid.ml.configs.petri_segmentation_config import PetriSegmentationConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest, TrainingManifestItem
from blueberry_microid.ml.reports.petri_segmentation_report import (
    PetriCandidateRegionResult,
    PetriSegmentationItemError,
    PetriSegmentationReport,
)


class ClassicalPetriSegmenter:
    """Classical OpenCV candidate-region segmentation for Petri images only.

    This is an explainable prototype: grayscale/blur/threshold/morphology/
    contours and geometry. It never uses OpenCV DNN, YOLO, pretrained models,
    deep learning, micro images, taxonomy, or diagnostic labels.
    """

    def segment(self, manifest: TrainingManifest, config: PetriSegmentationConfig) -> PetriSegmentationReport:
        regions: list[PetriCandidateRegionResult] = []
        errors: list[PetriSegmentationItemError] = []
        processed = 0

        for item in manifest.items:
            item_regions, error = self._segment_item(item, config)
            if error is not None:
                errors.append(error)
                continue
            processed += 1
            regions.extend(item_regions)

        failed = len(errors)
        status = _status_for(processed, failed, len(manifest.items))
        mean_regions = round(len(regions) / processed, 6) if processed else None
        summary = {
            "algorithm": config.algorithm,
            "threshold_method": config.threshold_method,
            "processed_only_modality": "petri",
            "total_candidate_regions": len(regions),
            "mean_regions_per_image": mean_regions,
            "error_count": failed,
            "errors": [
                {
                    "dataset_item_id": error.dataset_item_id,
                    "dataset_split_item_id": error.dataset_split_item_id,
                    "petri_image_path": error.petri_image_path,
                    "message": error.message,
                }
                for error in errors
            ],
            "contains_taxonomy": False,
            "contains_deep_learning": False,
            "contains_model_metrics": False,
            "candidate_region_notice": "Candidate regions are geometric segments, not confirmed colonies.",
        }
        return PetriSegmentationReport(
            status=status,
            is_completed=status != PetriSegmentationStatus.FAILED,
            errors=errors,
            warnings=[],
            total_items=len(manifest.items),
            processed_petri_images=processed,
            failed_petri_images=failed,
            total_regions_detected=len(regions),
            mean_regions_per_image=mean_regions,
            regions=regions,
            summary=summary,
        )

    def _segment_item(
        self, item: TrainingManifestItem, config: PetriSegmentationConfig
    ) -> tuple[list[PetriCandidateRegionResult], Optional[PetriSegmentationItemError]]:
        path = item.petri_image_path

        def _error(message: str, error_path: Optional[str] = path) -> tuple[list[PetriCandidateRegionResult], PetriSegmentationItemError]:
            return [], PetriSegmentationItemError(
                dataset_item_id=item.dataset_item_id,
                dataset_split_item_id=item.dataset_split_item_id,
                petri_image_path=error_path,
                message=message,
            )

        if not item.dataset_item_id or not item.dataset_split_item_id:
            return _error("manifest item is missing dataset item references")
        if not path or not path.strip():
            return _error("Petri image path is empty", None)
        if not os.path.exists(path):
            return _error(f"Petri image file does not exist: {path}")

        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if image is None:
            return _error(f"Petri image could not be read by OpenCV: {path}")

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if config.convert_to_grayscale else _as_gray(image)
            working = gray
            if config.blur_enabled:
                working = cv2.GaussianBlur(working, (config.blur_kernel_size, config.blur_kernel_size), 0)
            mask = self._threshold(working, config)
            mask = self._morphology(mask, config)
            candidates = self._regions_from_mask(mask, gray, item, path, config)
        except cv2.error as exc:
            return _error(f"Petri segmentation failed: {exc}")

        return candidates, None

    def _threshold(self, gray: np.ndarray, config: PetriSegmentationConfig) -> np.ndarray:
        # By default, darker regions on a lighter Petri background become
        # foreground. invert_threshold flips that assumption for bright-on-dark
        # captures.
        binary_type = cv2.THRESH_BINARY if config.invert_threshold else cv2.THRESH_BINARY_INV
        if config.threshold_method == "otsu":
            _threshold, mask = cv2.threshold(gray, 0, 255, binary_type | cv2.THRESH_OTSU)
            return mask
        if config.threshold_method == "manual":
            assert config.manual_threshold is not None
            _threshold, mask = cv2.threshold(gray, config.manual_threshold, 255, binary_type)
            return mask
        adaptive_type = cv2.THRESH_BINARY if config.invert_threshold else cv2.THRESH_BINARY_INV
        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            adaptive_type,
            11,
            2,
        )

    def _morphology(self, mask: np.ndarray, config: PetriSegmentationConfig) -> np.ndarray:
        kernel = np.ones((config.morphology_kernel_size, config.morphology_kernel_size), dtype=np.uint8)
        working = mask
        if config.morphological_opening:
            working = cv2.morphologyEx(working, cv2.MORPH_OPEN, kernel)
        if config.morphological_closing:
            working = cv2.morphologyEx(working, cv2.MORPH_CLOSE, kernel)
        return working

    def _regions_from_mask(
        self,
        mask: np.ndarray,
        gray: np.ndarray,
        item: TrainingManifestItem,
        path: str,
        config: PetriSegmentationConfig,
    ) -> list[PetriCandidateRegionResult]:
        contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rows: list[tuple[tuple[int, int, int, int], PetriCandidateRegionResult]] = []
        height, width = gray.shape[:2]

        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < config.min_region_area_px:
                continue
            if config.max_region_area_px is not None and area > config.max_region_area_px:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if config.exclude_border_regions and _touches_border(x, y, w, h, width, height, config.border_margin_px):
                continue
            perimeter = float(cv2.arcLength(contour, True))
            circularity = _circularity(area, perimeter)
            if config.min_circularity is not None and (circularity is None or circularity < config.min_circularity):
                continue
            moments = cv2.moments(contour)
            if moments["m00"] != 0:
                centroid_x = float(moments["m10"] / moments["m00"])
                centroid_y = float(moments["m01"] / moments["m00"])
            else:
                centroid_x = float(x + w / 2)
                centroid_y = float(y + h / 2)
            hull = cv2.convexHull(contour)
            hull_area = float(cv2.contourArea(hull))
            solidity = round(area / hull_area, 6) if hull_area > 0 else None
            contour_mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.drawContours(contour_mask, [contour], -1, 255, thickness=-1)
            mean_intensity = float(cv2.mean(gray, mask=contour_mask)[0])

            rows.append(
                (
                    (y, x, h, w),
                    PetriCandidateRegionResult(
                        dataset_item_id=item.dataset_item_id or "",
                        dataset_split_item_id=item.dataset_split_item_id or "",
                        split=item.split,
                        petri_image_path=path,
                        region_index=0,
                        area_px=round(area, 6),
                        perimeter_px=round(perimeter, 6),
                        centroid_x=round(centroid_x, 6),
                        centroid_y=round(centroid_y, 6),
                        bbox_x=int(x),
                        bbox_y=int(y),
                        bbox_width=int(w),
                        bbox_height=int(h),
                        circularity=round(circularity, 6) if circularity is not None else None,
                        solidity=solidity,
                        mean_intensity=round(mean_intensity, 6),
                        region_features={
                            "candidate_region": True,
                            "classification": None,
                            "taxonomy": None,
                            "diagnostic_claim": None,
                            "extraction_version": config.extraction_version,
                        },
                    ),
                )
            )

        rows.sort(key=lambda row: row[0])
        if config.max_regions is not None:
            rows = rows[: config.max_regions]
        return [_with_region_index(row, index) for index, (_key, row) in enumerate(rows)]


def _as_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _circularity(area: float, perimeter: float) -> Optional[float]:
    if perimeter <= 0:
        return None
    return float(4 * np.pi * area / (perimeter * perimeter))


def _touches_border(x: int, y: int, width: int, height: int, image_width: int, image_height: int, margin: int) -> bool:
    return x <= margin or y <= margin or x + width >= image_width - margin or y + height >= image_height - margin


def _with_region_index(row: PetriCandidateRegionResult, index: int) -> PetriCandidateRegionResult:
    return PetriCandidateRegionResult(
        dataset_item_id=row.dataset_item_id,
        dataset_split_item_id=row.dataset_split_item_id,
        split=row.split,
        petri_image_path=row.petri_image_path,
        region_index=index,
        area_px=row.area_px,
        perimeter_px=row.perimeter_px,
        centroid_x=row.centroid_x,
        centroid_y=row.centroid_y,
        bbox_x=row.bbox_x,
        bbox_y=row.bbox_y,
        bbox_width=row.bbox_width,
        bbox_height=row.bbox_height,
        circularity=row.circularity,
        solidity=row.solidity,
        mean_intensity=row.mean_intensity,
        region_features=row.region_features,
    )


def _status_for(processed: int, failed: int, total: int) -> PetriSegmentationStatus:
    if total == 0 or processed == 0 and failed > 0:
        return PetriSegmentationStatus.FAILED
    if failed > 0:
        return PetriSegmentationStatus.PARTIAL
    return PetriSegmentationStatus.COMPLETED
