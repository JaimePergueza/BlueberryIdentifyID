from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.dataset_split import DatasetSplit


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PetriSegmentationRegion:
    """One classical candidate region detected in a Petri image.

    A region is a geometric candidate only. It is not a confirmed colony,
    not a class prediction, and never a genus/species label.
    """

    segmentation_run_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    split: DatasetSplit
    petri_image_path: str
    region_index: int
    area_px: float
    centroid_x: float
    centroid_y: float
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    id: UUID = field(default_factory=uuid4)
    perimeter_px: Optional[float] = None
    circularity: Optional[float] = None
    solidity: Optional[float] = None
    mean_intensity: Optional[float] = None
    region_features: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)
