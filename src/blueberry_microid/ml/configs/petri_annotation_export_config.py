from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from blueberry_microid.domain.enums.petri_annotation_export_decision_filter import (
    PetriAnnotationExportDecisionFilter,
)
from blueberry_microid.domain.enums.petri_annotation_export_format import PetriAnnotationExportFormat


_FORBIDDEN_CATEGORY_TERMS = (
    "bacteria",
    "fungi",
    "fungus",
    "colony",
    "species",
    "genus",
    "taxon",
    "diagnosis",
)


@dataclass(frozen=True)
class PetriAnnotationExportConfig:
    export_format: PetriAnnotationExportFormat = PetriAnnotationExportFormat.BLUEBERRY_MANIFEST
    decision_filter: PetriAnnotationExportDecisionFilter = PetriAnnotationExportDecisionFilter.VALID_ONLY
    include_corrected_bbox: bool = True
    include_original_bbox: bool = True
    include_review_metadata: bool = True
    include_split: bool = True
    category_name: str = "candidate_region"
    category_id: int = 1
    normalize_yolo_coordinates: bool = True
    include_non_final_reviews: bool = False
    copy_images: bool = False
    output_dir: Optional[str] = None
    fail_on_missing_image_dimensions: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "export_format", PetriAnnotationExportFormat(self.export_format))
        object.__setattr__(
            self,
            "decision_filter",
            PetriAnnotationExportDecisionFilter(self.decision_filter),
        )
        if self.copy_images:
            raise ValueError("copy_images is not supported in this phase; original images are never copied")
        if self.category_id <= 0:
            raise ValueError("category_id must be positive")
        category_name = self.category_name.strip()
        if not category_name:
            raise ValueError("category_name must not be blank")
        lowered = category_name.lower()
        if any(term in lowered for term in _FORBIDDEN_CATEGORY_TERMS):
            raise ValueError("category_name must remain generic and must not contain taxonomy or diagnosis terms")
        object.__setattr__(self, "category_name", category_name)

    def to_dict(self) -> dict:
        return {
            "export_format": self.export_format.value,
            "decision_filter": self.decision_filter.value,
            "include_corrected_bbox": self.include_corrected_bbox,
            "include_original_bbox": self.include_original_bbox,
            "include_review_metadata": self.include_review_metadata,
            "include_split": self.include_split,
            "category_name": self.category_name,
            "category_id": self.category_id,
            "normalize_yolo_coordinates": self.normalize_yolo_coordinates,
            "include_non_final_reviews": self.include_non_final_reviews,
            "copy_images": self.copy_images,
            "output_dir": self.output_dir,
            "fail_on_missing_image_dimensions": self.fail_on_missing_image_dimensions,
        }
