from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.image_feature_vector import ImageFeatureVector
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_modality import ImageModality


class ImageFeatureVectorRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, feature_vectors: list[ImageFeatureVector]) -> list[ImageFeatureVector]:
        raise NotImplementedError

    @abstractmethod
    def list_by_feature_extraction_run_id(self, feature_extraction_run_id: UUID) -> list[ImageFeatureVector]:
        raise NotImplementedError

    @abstractmethod
    def list_by_feature_extraction_run_id_and_modality(
        self, feature_extraction_run_id: UUID, modality: ImageModality
    ) -> list[ImageFeatureVector]:
        raise NotImplementedError

    @abstractmethod
    def list_by_feature_extraction_run_id_and_split(
        self, feature_extraction_run_id: UUID, split: DatasetSplit
    ) -> list[ImageFeatureVector]:
        raise NotImplementedError
