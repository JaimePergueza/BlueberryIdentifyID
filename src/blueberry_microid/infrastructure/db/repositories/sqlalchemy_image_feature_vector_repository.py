from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.image_feature_vector_repository import ImageFeatureVectorRepositoryPort
from blueberry_microid.domain.entities.image_feature_vector import ImageFeatureVector
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.infrastructure.db.models.image_feature_vector import ImageFeatureVectorModel
from blueberry_microid.infrastructure.db.repositories.mappers import image_feature_vector_to_entity


class SqlAlchemyImageFeatureVectorRepository(ImageFeatureVectorRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, feature_vectors: list[ImageFeatureVector]) -> list[ImageFeatureVector]:
        models = [
            ImageFeatureVectorModel(
                id=vector.id,
                feature_extraction_run_id=vector.feature_extraction_run_id,
                dataset_release_id=vector.dataset_release_id,
                dataset_item_id=vector.dataset_item_id,
                dataset_split_item_id=vector.dataset_split_item_id,
                split=vector.split.value,
                modality=vector.modality.value,
                image_path=vector.image_path,
                features=vector.features,
                preprocessing=vector.preprocessing,
                extraction_version=vector.extraction_version,
                created_at=vector.created_at,
            )
            for vector in feature_vectors
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [image_feature_vector_to_entity(model) for model in models]

    def list_by_feature_extraction_run_id(self, feature_extraction_run_id: UUID) -> list[ImageFeatureVector]:
        statement = (
            select(ImageFeatureVectorModel)
            .where(ImageFeatureVectorModel.feature_extraction_run_id == feature_extraction_run_id)
            .order_by(ImageFeatureVectorModel.created_at.asc(), ImageFeatureVectorModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [image_feature_vector_to_entity(model) for model in models]

    def list_by_feature_extraction_run_id_and_modality(
        self, feature_extraction_run_id: UUID, modality: ImageModality
    ) -> list[ImageFeatureVector]:
        statement = (
            select(ImageFeatureVectorModel)
            .where(
                ImageFeatureVectorModel.feature_extraction_run_id == feature_extraction_run_id,
                ImageFeatureVectorModel.modality == modality.value,
            )
            .order_by(ImageFeatureVectorModel.created_at.asc(), ImageFeatureVectorModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [image_feature_vector_to_entity(model) for model in models]

    def list_by_feature_extraction_run_id_and_split(
        self, feature_extraction_run_id: UUID, split: DatasetSplit
    ) -> list[ImageFeatureVector]:
        statement = (
            select(ImageFeatureVectorModel)
            .where(
                ImageFeatureVectorModel.feature_extraction_run_id == feature_extraction_run_id,
                ImageFeatureVectorModel.split == split.value,
            )
            .order_by(ImageFeatureVectorModel.created_at.asc(), ImageFeatureVectorModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [image_feature_vector_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
