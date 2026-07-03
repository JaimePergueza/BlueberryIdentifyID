from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_annotation_bbox_source import PetriAnnotationBboxSource


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PetriAnnotationExportItem:
    """One exported reviewed Petri annotation.

    The label is intentionally generic (`candidate_region` by default): it is
    not a colony confirmation, taxon, genus, species, or diagnosis.
    """

    export_run_id: UUID
    petri_region_review_id: UUID
    petri_segmentation_region_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    split: DatasetSplit
    petri_image_path: str
    export_label: str
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    bbox_source: PetriAnnotationBboxSource
    export_payload: dict
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if self.bbox_width <= 0:
            raise ValueError("bbox_width must be positive")
        if self.bbox_height <= 0:
            raise ValueError("bbox_height must be positive")
