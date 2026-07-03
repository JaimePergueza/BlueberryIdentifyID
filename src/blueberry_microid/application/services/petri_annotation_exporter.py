from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from PIL import Image

from blueberry_microid.domain.entities.petri_annotation_export_item import PetriAnnotationExportItem
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun
from blueberry_microid.domain.enums.petri_annotation_bbox_source import PetriAnnotationBboxSource
from blueberry_microid.domain.enums.petri_annotation_export_decision_filter import (
    PetriAnnotationExportDecisionFilter,
)
from blueberry_microid.domain.enums.petri_annotation_export_format import PetriAnnotationExportFormat
from blueberry_microid.domain.enums.petri_region_review_decision import PetriRegionReviewDecision
from blueberry_microid.ml.configs.petri_annotation_export_config import PetriAnnotationExportConfig


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


@dataclass(frozen=True)
class PetriAnnotationExportResult:
    output_manifest: dict[str, Any]
    items: list[PetriAnnotationExportItem]
    summary: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class PetriAnnotationExporter:
    """Build supervised annotation payloads from final human reviews.

    This is a format exporter only. It never trains YOLO, never imports deep
    learning frameworks, never copies images, and never emits taxonomy.
    """

    def export(
        self,
        *,
        segmentation_run: PetriSegmentationRun,
        regions: list[PetriSegmentationRegion],
        reviews: list[PetriRegionReview],
        config: PetriAnnotationExportConfig,
        export_run_id: UUID,
    ) -> PetriAnnotationExportResult:
        regions_by_id = {region.id: region for region in regions}
        selected_reviews, skipped_count = self._select_reviews(reviews, config)
        selected_reviews = [
            review for review in selected_reviews if review.petri_segmentation_region_id in regions_by_id
        ]
        selected_reviews.sort(key=lambda review: self._sort_key(review, regions_by_id))

        warnings: list[str] = []
        errors: list[str] = []
        image_dimensions: dict[str, tuple[int, int] | None] = {}
        items: list[PetriAnnotationExportItem] = []

        for review in selected_reviews:
            region = regions_by_id[review.petri_segmentation_region_id]
            bbox, bbox_source = self._effective_bbox(region, review, config)
            image_size = self._image_dimensions(region.petri_image_path, image_dimensions)
            if config.export_format == PetriAnnotationExportFormat.YOLO_TXT and image_size is None:
                message = f"missing image dimensions for YOLO export: {region.petri_image_path}"
                if config.fail_on_missing_image_dimensions:
                    errors.append(message)
                    continue
                warnings.append(message)

            payload = self._item_payload(review, region, bbox, bbox_source, config, image_size)
            items.append(
                PetriAnnotationExportItem(
                    export_run_id=export_run_id,
                    petri_region_review_id=review.id,
                    petri_segmentation_region_id=region.id,
                    dataset_release_id=region.dataset_release_id,
                    dataset_item_id=region.dataset_item_id,
                    dataset_split_item_id=region.dataset_split_item_id,
                    split=region.split,
                    petri_image_path=region.petri_image_path,
                    export_label=config.category_name,
                    bbox_x=bbox["x"],
                    bbox_y=bbox["y"],
                    bbox_width=bbox["width"],
                    bbox_height=bbox["height"],
                    bbox_source=bbox_source,
                    export_payload=payload,
                )
            )

        if errors:
            return PetriAnnotationExportResult(
                output_manifest={},
                items=[],
                summary=self._summary(segmentation_run, config, 0, skipped_count, warnings, errors),
                warnings=warnings,
                errors=errors,
            )

        manifest = self._manifest(segmentation_run, items, config, image_dimensions)
        summary = self._summary(segmentation_run, config, len(items), skipped_count, warnings, errors)
        manifest["summary"] = summary
        return PetriAnnotationExportResult(
            output_manifest=manifest,
            items=items,
            summary=summary,
            warnings=warnings,
            errors=errors,
        )

    def _select_reviews(
        self, reviews: list[PetriRegionReview], config: PetriAnnotationExportConfig
    ) -> tuple[list[PetriRegionReview], int]:
        if not config.include_non_final_reviews:
            reviews = [review for review in reviews if review.is_final]

        allowed = {
            PetriAnnotationExportDecisionFilter.VALID_ONLY: {PetriRegionReviewDecision.CANDIDATE_VALID},
            PetriAnnotationExportDecisionFilter.VALID_AND_UNCERTAIN: {
                PetriRegionReviewDecision.CANDIDATE_VALID,
                PetriRegionReviewDecision.CANDIDATE_UNCERTAIN,
            },
            PetriAnnotationExportDecisionFilter.ALL_FINAL_REVIEWS: set(PetriRegionReviewDecision),
        }[config.decision_filter]
        selected = [review for review in reviews if review.decision in allowed]
        return selected, len(reviews) - len(selected)

    @staticmethod
    def _effective_bbox(
        region: PetriSegmentationRegion,
        review: PetriRegionReview,
        config: PetriAnnotationExportConfig,
    ) -> tuple[dict[str, int], PetriAnnotationBboxSource]:
        corrected_complete = (
            review.corrected_bbox_x is not None
            and review.corrected_bbox_y is not None
            and review.corrected_bbox_width is not None
            and review.corrected_bbox_height is not None
        )
        if config.include_corrected_bbox and corrected_complete:
            return (
                {
                    "x": review.corrected_bbox_x,
                    "y": review.corrected_bbox_y,
                    "width": review.corrected_bbox_width,
                    "height": review.corrected_bbox_height,
                },
                PetriAnnotationBboxSource.CORRECTED,
            )
        return (
            {
                "x": region.bbox_x,
                "y": region.bbox_y,
                "width": region.bbox_width,
                "height": region.bbox_height,
            },
            PetriAnnotationBboxSource.ORIGINAL,
        )

    @staticmethod
    def _image_dimensions(
        image_path: str,
        cache: dict[str, tuple[int, int] | None],
    ) -> tuple[int, int] | None:
        if image_path in cache:
            return cache[image_path]
        try:
            with Image.open(Path(image_path)) as image:
                cache[image_path] = (int(image.width), int(image.height))
        except Exception:
            cache[image_path] = None
        return cache[image_path]

    def _item_payload(
        self,
        review: PetriRegionReview,
        region: PetriSegmentationRegion,
        bbox: dict[str, int],
        bbox_source: PetriAnnotationBboxSource,
        config: PetriAnnotationExportConfig,
        image_size: Optional[tuple[int, int]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "label": config.category_name,
            "bbox": bbox,
            "bbox_source": bbox_source.value,
            "decision": review.decision.value,
            "petri_image_path": region.petri_image_path,
        }
        if config.include_split:
            payload["split"] = region.split.value
        if config.include_original_bbox:
            payload["original_bbox"] = {
                "x": region.bbox_x,
                "y": region.bbox_y,
                "width": region.bbox_width,
                "height": region.bbox_height,
            }
        if image_size is not None:
            payload["image_width"], payload["image_height"] = image_size
        if config.include_review_metadata:
            payload["review_metadata"] = {
                "petri_region_review_id": str(review.id),
                "is_final": review.is_final,
                "confidence_score": review.confidence_score,
                "created_at": _iso(review.created_at),
            }
        return payload

    def _manifest(
        self,
        segmentation_run: PetriSegmentationRun,
        items: list[PetriAnnotationExportItem],
        config: PetriAnnotationExportConfig,
        image_dimensions: dict[str, tuple[int, int] | None],
    ) -> dict[str, Any]:
        if config.export_format == PetriAnnotationExportFormat.COCO_JSON:
            return self._coco_manifest(segmentation_run, items, config, image_dimensions)
        if config.export_format == PetriAnnotationExportFormat.YOLO_TXT:
            return self._yolo_manifest(segmentation_run, items, config, image_dimensions)
        return self._blueberry_manifest(segmentation_run, items, config, image_dimensions)

    def _blueberry_manifest(
        self,
        segmentation_run: PetriSegmentationRun,
        items: list[PetriAnnotationExportItem],
        config: PetriAnnotationExportConfig,
        image_dimensions: dict[str, tuple[int, int] | None],
    ) -> dict[str, Any]:
        images = self._images(items, image_dimensions)
        return {
            "format": PetriAnnotationExportFormat.BLUEBERRY_MANIFEST.value,
            "dataset_release_id": str(segmentation_run.dataset_release_id),
            "petri_segmentation_run_id": str(segmentation_run.id),
            "generated_at": _iso(datetime.now(timezone.utc)),
            "category": {"id": config.category_id, "name": config.category_name},
            "images": images,
            "annotations": [
                {
                    "annotation_id": str(item.id),
                    "image_id": self._image_id(item.petri_image_path),
                    "petri_region_review_id": str(item.petri_region_review_id),
                    "petri_segmentation_region_id": str(item.petri_segmentation_region_id),
                    "bbox": [item.bbox_x, item.bbox_y, item.bbox_width, item.bbox_height],
                    "bbox_source": item.bbox_source.value,
                    "decision": item.export_payload["decision"],
                    "split": item.split.value,
                    "label": item.export_label,
                }
                for item in items
            ],
        }

    def _coco_manifest(
        self,
        segmentation_run: PetriSegmentationRun,
        items: list[PetriAnnotationExportItem],
        config: PetriAnnotationExportConfig,
        image_dimensions: dict[str, tuple[int, int] | None],
    ) -> dict[str, Any]:
        images = []
        for image in self._images(items, image_dimensions):
            images.append(
                {
                    "id": image["image_id"],
                    "file_name": image["petri_image_path"],
                    "width": image.get("width"),
                    "height": image.get("height"),
                    "split": image.get("split"),
                }
            )
        return {
            "info": {
                "description": "BlueberryMicroID reviewed Petri candidate-region annotations",
                "generated_at": _iso(datetime.now(timezone.utc)),
                "dataset_release_id": str(segmentation_run.dataset_release_id),
                "petri_segmentation_run_id": str(segmentation_run.id),
            },
            "images": images,
            "annotations": [
                {
                    "id": str(item.id),
                    "image_id": self._image_id(item.petri_image_path),
                    "category_id": config.category_id,
                    "bbox": [item.bbox_x, item.bbox_y, item.bbox_width, item.bbox_height],
                    "area": item.bbox_width * item.bbox_height,
                    "iscrowd": 0,
                }
                for item in items
            ],
            "categories": [{"id": config.category_id, "name": config.category_name}],
        }

    def _yolo_manifest(
        self,
        segmentation_run: PetriSegmentationRun,
        items: list[PetriAnnotationExportItem],
        config: PetriAnnotationExportConfig,
        image_dimensions: dict[str, tuple[int, int] | None],
    ) -> dict[str, Any]:
        grouped: dict[str, dict[str, Any]] = {}
        for item in items:
            width, height = image_dimensions[item.petri_image_path] or (0, 0)
            x_center = (item.bbox_x + item.bbox_width / 2) / width
            y_center = (item.bbox_y + item.bbox_height / 2) / height
            bbox_width = item.bbox_width / width
            bbox_height = item.bbox_height / height
            entry = grouped.setdefault(
                item.petri_image_path,
                {
                    "image_path": item.petri_image_path,
                    "split": item.split.value,
                    "class_id": 0,
                    "category_name": config.category_name,
                    "lines": [],
                },
            )
            entry["lines"].append(f"0 {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}")
        return {
            "format": PetriAnnotationExportFormat.YOLO_TXT.value,
            "dataset_release_id": str(segmentation_run.dataset_release_id),
            "petri_segmentation_run_id": str(segmentation_run.id),
            "generated_at": _iso(datetime.now(timezone.utc)),
            "labels": [grouped[path] for path in sorted(grouped)],
            "category": {"class_id": 0, "name": config.category_name},
        }

    @staticmethod
    def _images(
        items: list[PetriAnnotationExportItem],
        image_dimensions: dict[str, tuple[int, int] | None],
    ) -> list[dict[str, Any]]:
        images: dict[str, dict[str, Any]] = {}
        for item in items:
            width_height = image_dimensions.get(item.petri_image_path)
            image = images.setdefault(
                item.petri_image_path,
                {
                    "image_id": PetriAnnotationExporter._image_id(item.petri_image_path),
                    "petri_image_path": item.petri_image_path,
                    "split": item.split.value,
                },
            )
            if width_height is not None:
                image["width"], image["height"] = width_height
        return [images[path] for path in sorted(images)]

    @staticmethod
    def _image_id(image_path: str) -> str:
        return image_path

    @staticmethod
    def _sort_key(review: PetriRegionReview, regions_by_id: dict[UUID, PetriSegmentationRegion]) -> tuple[str, int, str]:
        region = regions_by_id[review.petri_segmentation_region_id]
        return (region.petri_image_path, region.region_index, str(review.id))

    @staticmethod
    def _summary(
        segmentation_run: PetriSegmentationRun,
        config: PetriAnnotationExportConfig,
        exported_count: int,
        skipped_count: int,
        warnings: list[str],
        errors: list[str],
    ) -> dict[str, Any]:
        return {
            "dataset_release_id": str(segmentation_run.dataset_release_id),
            "petri_segmentation_run_id": str(segmentation_run.id),
            "export_format": config.export_format.value,
            "decision_filter": config.decision_filter.value,
            "exported_annotation_count": exported_count,
            "skipped_review_count": skipped_count,
            "warning_count": len(warnings),
            "error_count": len(errors),
            "warnings": warnings,
            "errors": errors,
            "copy_images": False,
            "contains_taxonomy": False,
            "contains_masks": False,
            "contains_training": False,
            "model_family": None,
        }
