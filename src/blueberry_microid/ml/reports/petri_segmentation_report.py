from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus


@dataclass(frozen=True, slots=True)
class PetriCandidateRegionResult:
    dataset_item_id: str
    dataset_split_item_id: str
    split: str
    petri_image_path: str
    region_index: int
    area_px: float
    perimeter_px: Optional[float]
    centroid_x: float
    centroid_y: float
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    circularity: Optional[float]
    solidity: Optional[float]
    mean_intensity: Optional[float]
    region_features: dict


@dataclass(frozen=True, slots=True)
class PetriSegmentationItemError:
    dataset_item_id: Optional[str]
    dataset_split_item_id: Optional[str]
    petri_image_path: Optional[str]
    message: str


@dataclass(frozen=True, slots=True)
class PetriSegmentationReport:
    status: PetriSegmentationStatus
    is_completed: bool
    errors: list[PetriSegmentationItemError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_items: int = 0
    processed_petri_images: int = 0
    failed_petri_images: int = 0
    total_regions_detected: int = 0
    mean_regions_per_image: Optional[float] = None
    regions: list[PetriCandidateRegionResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
