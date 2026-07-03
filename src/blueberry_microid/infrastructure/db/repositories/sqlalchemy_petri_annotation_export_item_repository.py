from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.petri_annotation_export_item_repository import (
    PetriAnnotationExportItemRepositoryPort,
)
from blueberry_microid.domain.entities.petri_annotation_export_item import PetriAnnotationExportItem
from blueberry_microid.infrastructure.db.models.petri_annotation_export_item import PetriAnnotationExportItemModel
from blueberry_microid.infrastructure.db.repositories.mappers import petri_annotation_export_item_to_entity


class SqlAlchemyPetriAnnotationExportItemRepository(PetriAnnotationExportItemRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, items: list[PetriAnnotationExportItem]) -> list[PetriAnnotationExportItem]:
        models = [
            PetriAnnotationExportItemModel(
                id=item.id,
                export_run_id=item.export_run_id,
                petri_region_review_id=item.petri_region_review_id,
                petri_segmentation_region_id=item.petri_segmentation_region_id,
                dataset_release_id=item.dataset_release_id,
                dataset_item_id=item.dataset_item_id,
                dataset_split_item_id=item.dataset_split_item_id,
                split=item.split.value,
                petri_image_path=item.petri_image_path,
                export_label=item.export_label,
                bbox_x=item.bbox_x,
                bbox_y=item.bbox_y,
                bbox_width=item.bbox_width,
                bbox_height=item.bbox_height,
                bbox_source=item.bbox_source.value,
                export_payload=item.export_payload,
                created_at=item.created_at,
            )
            for item in items
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        return items

    def list_by_export_run_id(self, export_run_id: UUID) -> list[PetriAnnotationExportItem]:
        statement = (
            select(PetriAnnotationExportItemModel)
            .where(PetriAnnotationExportItemModel.export_run_id == export_run_id)
            .order_by(
                PetriAnnotationExportItemModel.petri_image_path.asc(),
                PetriAnnotationExportItemModel.created_at.asc(),
                PetriAnnotationExportItemModel.id.asc(),
            )
        )
        return [petri_annotation_export_item_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
