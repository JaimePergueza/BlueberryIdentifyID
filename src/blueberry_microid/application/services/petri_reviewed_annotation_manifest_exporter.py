from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from blueberry_microid.application.exceptions import PetriSegmentationRunNotFoundError
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.application.ports.petri_segmentation_run_repository import PetriSegmentationRunRepositoryPort
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class PetriReviewedAnnotationManifestExporter:
    """Build a deterministic manifest of human-reviewed PetriSegmentationRegion
    candidates for one PetriSegmentationRun.

    Pure metadata — never image bytes, masks, taxonomy, or a YOLO/label-file
    export format. Only final reviews are included by default (a candidate
    region is annotation-ready only once it has a stable final decision);
    `include_non_final=True` additionally includes historical reviews for
    audit purposes. Ordered deterministically by (petri_image_path,
    region_index, review id), never by incidental database fetch order.
    """

    def __init__(
        self,
        segmentation_run_repository: PetriSegmentationRunRepositoryPort,
        region_repository: PetriSegmentationRegionRepositoryPort,
        review_repository: PetriRegionReviewRepositoryPort,
    ) -> None:
        self._segmentation_run_repository = segmentation_run_repository
        self._region_repository = region_repository
        self._review_repository = review_repository

    def export(self, segmentation_run_id: UUID, *, include_non_final: bool = False) -> dict[str, Any]:
        run = self._segmentation_run_repository.get_by_id(segmentation_run_id)
        if run is None:
            raise PetriSegmentationRunNotFoundError(f"petri_segmentation_run '{segmentation_run_id}' does not exist")

        regions_by_id: dict[UUID, PetriSegmentationRegion] = {
            region.id: region
            for region in self._region_repository.list_by_segmentation_run_id(segmentation_run_id)
        }
        reviews = self._review_repository.list_by_segmentation_run_id(segmentation_run_id)
        if not include_non_final:
            reviews = [review for review in reviews if review.is_final]

        reviews.sort(
            key=lambda review: (
                self._region_sort_key(review, regions_by_id),
                str(review.id),
            )
        )

        decision_distribution: dict[str, int] = {}
        reviewed_region_ids: set[UUID] = set()
        final_reviewed_region_ids: set[UUID] = set()
        annotations: list[dict[str, Any]] = []

        for review in reviews:
            region = regions_by_id.get(review.petri_segmentation_region_id)
            if region is None:
                continue

            reviewed_region_ids.add(region.id)
            if review.is_final:
                final_reviewed_region_ids.add(region.id)
            decision_distribution[review.decision.value] = decision_distribution.get(review.decision.value, 0) + 1

            original_bbox = {
                "x": region.bbox_x,
                "y": region.bbox_y,
                "width": region.bbox_width,
                "height": region.bbox_height,
            }
            corrected_bbox = self._corrected_bbox(review)
            effective_bbox = corrected_bbox if corrected_bbox is not None else original_bbox

            annotations.append(
                {
                    "petri_segmentation_region_id": str(region.id),
                    "dataset_item_id": str(region.dataset_item_id),
                    "dataset_split_item_id": str(region.dataset_split_item_id),
                    "split": region.split.value,
                    "petri_image_path": region.petri_image_path,
                    "original_bbox": original_bbox,
                    "corrected_bbox": corrected_bbox,
                    "effective_bbox": effective_bbox,
                    "decision": review.decision.value,
                    "confidence_score": review.confidence_score,
                    "reviewer_id": review.reviewer_id,
                    "is_final": review.is_final,
                    "created_at": _iso(review.created_at),
                }
            )

        return {
            "dataset_release_id": str(run.dataset_release_id),
            "petri_segmentation_run_id": str(run.id),
            "generated_at": _iso(datetime.now(timezone.utc)),
            "total_regions": len(regions_by_id),
            "reviewed_regions": len(reviewed_region_ids),
            "final_reviewed_regions": len(final_reviewed_region_ids),
            "decision_distribution": decision_distribution,
            "annotations": annotations,
        }

    @staticmethod
    def _region_sort_key(
        review: PetriRegionReview, regions_by_id: dict[UUID, PetriSegmentationRegion]
    ) -> tuple[str, int]:
        region = regions_by_id.get(review.petri_segmentation_region_id)
        if region is None:
            return ("", 0)
        return (region.petri_image_path, region.region_index)

    @staticmethod
    def _corrected_bbox(review: PetriRegionReview) -> dict[str, int] | None:
        if (
            review.corrected_bbox_x is None
            and review.corrected_bbox_y is None
            and review.corrected_bbox_width is None
            and review.corrected_bbox_height is None
        ):
            return None
        return {
            "x": review.corrected_bbox_x,
            "y": review.corrected_bbox_y,
            "width": review.corrected_bbox_width,
            "height": review.corrected_bbox_height,
        }
