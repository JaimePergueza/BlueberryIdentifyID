from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus
from blueberry_microid.domain.enums.image_modality import ImageModality


@dataclass(frozen=True, slots=True)
class FeatureVectorResult:
    """One successfully extracted Petri or micro feature vector, ready to be
    turned into a persisted `ImageFeatureVector` once a run id exists."""

    dataset_item_id: str
    dataset_split_item_id: str
    split: str
    modality: ImageModality
    image_path: str
    features: dict
    preprocessing: dict


@dataclass(frozen=True, slots=True)
class ImageFeatureExtractionItemError:
    """One image that could not be turned into a feature vector."""

    dataset_item_id: str
    dataset_split_item_id: str
    modality: ImageModality
    image_path: Optional[str]
    message: str


@dataclass(frozen=True, slots=True)
class ImageFeatureExtractionReport:
    """Result of running `ImageFeatureExtractor` over one DatasetRelease
    manifest. Only small technical scalars/histograms per image — never
    image bytes, tensors, model artifacts, or classification metrics."""

    status: ImageFeatureExtractionStatus
    is_completed: bool
    vectors: list[FeatureVectorResult] = field(default_factory=list)
    errors: list[ImageFeatureExtractionItemError] = field(default_factory=list)
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    petri_feature_count: int = 0
    micro_feature_count: int = 0
    summary: dict = field(default_factory=dict)

    @property
    def total_feature_vectors(self) -> int:
        return len(self.vectors)
