from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.image_feature_extraction_run import ImageFeatureExtractionRun
from blueberry_microid.domain.entities.image_feature_vector import ImageFeatureVector
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.ml.configs.image_feature_extraction_config import ImageFeatureExtractionConfig


@dataclass(frozen=True, slots=True)
class CreateImageFeatureExtractionRunRequest:
    dataset_release_id: UUID
    image_audit_run_id: UUID
    config: ImageFeatureExtractionConfig = field(default_factory=ImageFeatureExtractionConfig)
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ImageFeatureVectorDTO:
    id: UUID
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
    created_at: datetime

    @classmethod
    def from_entity(cls, vector: ImageFeatureVector) -> "ImageFeatureVectorDTO":
        return cls(
            id=vector.id,
            feature_extraction_run_id=vector.feature_extraction_run_id,
            dataset_release_id=vector.dataset_release_id,
            dataset_item_id=vector.dataset_item_id,
            dataset_split_item_id=vector.dataset_split_item_id,
            split=vector.split,
            modality=vector.modality,
            image_path=vector.image_path,
            features=vector.features,
            preprocessing=vector.preprocessing,
            extraction_version=vector.extraction_version,
            created_at=vector.created_at,
        )


@dataclass(frozen=True, slots=True)
class ImageFeatureExtractionRunDTO:
    id: UUID
    dataset_release_id: UUID
    image_audit_run_id: UUID
    status: ImageFeatureExtractionStatus
    is_completed: bool
    config: dict
    total_items: int
    processed_items: int
    failed_items: int
    total_feature_vectors: int
    petri_feature_count: int
    micro_feature_count: int
    summary: dict
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]
    vectors: list[ImageFeatureVectorDTO] = field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        extraction_run: ImageFeatureExtractionRun,
        vectors: Optional[list[ImageFeatureVector]] = None,
    ) -> "ImageFeatureExtractionRunDTO":
        return cls(
            id=extraction_run.id,
            dataset_release_id=extraction_run.dataset_release_id,
            image_audit_run_id=extraction_run.image_audit_run_id,
            status=extraction_run.status,
            is_completed=extraction_run.is_completed,
            config=extraction_run.config,
            total_items=extraction_run.total_items,
            processed_items=extraction_run.processed_items,
            failed_items=extraction_run.failed_items,
            total_feature_vectors=extraction_run.total_feature_vectors,
            petri_feature_count=extraction_run.petri_feature_count,
            micro_feature_count=extraction_run.micro_feature_count,
            summary=extraction_run.summary,
            started_at=extraction_run.started_at,
            completed_at=extraction_run.completed_at,
            created_at=extraction_run.created_at,
            created_by=extraction_run.created_by,
            notes=extraction_run.notes,
            error_message=extraction_run.error_message,
            vectors=[ImageFeatureVectorDTO.from_entity(vector) for vector in vectors or []],
        )


def image_feature_extraction_config_to_dict(config: ImageFeatureExtractionConfig) -> dict:
    return asdict(config)
