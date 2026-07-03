from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_modality import ImageModality


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ImageFeatureVector:
    """One Petri or micro image's simple, non-deep, reproducible feature
    vector for a specific ImageFeatureExtractionRun.

    A single DatasetItem produces up to two vectors (one per modality). Only
    small technical scalars/histograms live in `features` — never taxonomy,
    a model prediction, or raw pixel/tensor data.
    """

    feature_extraction_run_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    split: DatasetSplit
    modality: ImageModality
    image_path: str
    features: dict
    preprocessing: dict
    extraction_version: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
