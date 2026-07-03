from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.infrastructure.db.models.petri_segmentation_region import PetriSegmentationRegionModel
from blueberry_microid.infrastructure.db.repositories.mappers import petri_segmentation_region_to_entity


class SqlAlchemyPetriSegmentationRegionRepository(PetriSegmentationRegionRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, regions: list[PetriSegmentationRegion]) -> list[PetriSegmentationRegion]:
        models = [
            PetriSegmentationRegionModel(
                id=region.id,
                segmentation_run_id=region.segmentation_run_id,
                dataset_release_id=region.dataset_release_id,
                dataset_item_id=region.dataset_item_id,
                dataset_split_item_id=region.dataset_split_item_id,
                split=region.split.value,
                petri_image_path=region.petri_image_path,
                region_index=region.region_index,
                area_px=region.area_px,
                perimeter_px=region.perimeter_px,
                centroid_x=region.centroid_x,
                centroid_y=region.centroid_y,
                bbox_x=region.bbox_x,
                bbox_y=region.bbox_y,
                bbox_width=region.bbox_width,
                bbox_height=region.bbox_height,
                circularity=region.circularity,
                solidity=region.solidity,
                mean_intensity=region.mean_intensity,
                region_features=region.region_features,
                created_at=region.created_at,
            )
            for region in regions
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [petri_segmentation_region_to_entity(model) for model in models]

    def list_by_segmentation_run_id(self, segmentation_run_id: UUID) -> list[PetriSegmentationRegion]:
        statement = (
            select(PetriSegmentationRegionModel)
            .where(PetriSegmentationRegionModel.segmentation_run_id == segmentation_run_id)
            .order_by(
                PetriSegmentationRegionModel.dataset_split_item_id.asc(),
                PetriSegmentationRegionModel.region_index.asc(),
            )
        )
        return [petri_segmentation_region_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def list_by_segmentation_run_id_and_split(
        self, segmentation_run_id: UUID, split: DatasetSplit
    ) -> list[PetriSegmentationRegion]:
        statement = (
            select(PetriSegmentationRegionModel)
            .where(
                PetriSegmentationRegionModel.segmentation_run_id == segmentation_run_id,
                PetriSegmentationRegionModel.split == split.value,
            )
            .order_by(
                PetriSegmentationRegionModel.dataset_split_item_id.asc(),
                PetriSegmentationRegionModel.region_index.asc(),
            )
        )
        return [petri_segmentation_region_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
