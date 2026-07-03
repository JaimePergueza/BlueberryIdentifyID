from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.image_feature_extraction_run import ImageFeatureExtractionRun


class ImageFeatureExtractionRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, extraction_run: ImageFeatureExtractionRun) -> ImageFeatureExtractionRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, extraction_run_id: UUID) -> Optional[ImageFeatureExtractionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[ImageFeatureExtractionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[ImageFeatureExtractionRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_image_audit_run_id(self, image_audit_run_id: UUID) -> list[ImageFeatureExtractionRun]:
        raise NotImplementedError
