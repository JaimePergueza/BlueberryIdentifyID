from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus
from blueberry_microid.ml.configs.petri_segmentation_config import PetriSegmentationConfig


@dataclass(frozen=True, slots=True)
class CreatePetriSegmentationRunRequest:
    dataset_release_id: UUID
    image_audit_run_id: Optional[UUID] = None
    config: PetriSegmentationConfig = field(default_factory=PetriSegmentationConfig)
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PetriSegmentationRegionDTO:
    id: UUID
    segmentation_run_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    split: DatasetSplit
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
    region_features: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, region: PetriSegmentationRegion) -> "PetriSegmentationRegionDTO":
        return cls(**region.__dict__)


@dataclass(frozen=True, slots=True)
class PetriSegmentationRunDTO:
    id: UUID
    dataset_release_id: UUID
    image_audit_run_id: Optional[UUID]
    status: PetriSegmentationStatus
    is_completed: bool
    config: dict
    total_items: int
    processed_petri_images: int
    failed_petri_images: int
    total_regions_detected: int
    mean_regions_per_image: Optional[float]
    summary: dict
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]
    regions: list[PetriSegmentationRegionDTO] = field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        segmentation_run: PetriSegmentationRun,
        regions: Optional[list[PetriSegmentationRegion]] = None,
    ) -> "PetriSegmentationRunDTO":
        return cls(
            id=segmentation_run.id,
            dataset_release_id=segmentation_run.dataset_release_id,
            image_audit_run_id=segmentation_run.image_audit_run_id,
            status=segmentation_run.status,
            is_completed=segmentation_run.is_completed,
            config=segmentation_run.config,
            total_items=segmentation_run.total_items,
            processed_petri_images=segmentation_run.processed_petri_images,
            failed_petri_images=segmentation_run.failed_petri_images,
            total_regions_detected=segmentation_run.total_regions_detected,
            mean_regions_per_image=segmentation_run.mean_regions_per_image,
            summary=segmentation_run.summary,
            started_at=segmentation_run.started_at,
            completed_at=segmentation_run.completed_at,
            created_at=segmentation_run.created_at,
            created_by=segmentation_run.created_by,
            notes=segmentation_run.notes,
            error_message=segmentation_run.error_message,
            regions=[PetriSegmentationRegionDTO.from_entity(region) for region in regions or []],
        )


def petri_segmentation_config_to_dict(config: PetriSegmentationConfig) -> dict:
    return asdict(config)
