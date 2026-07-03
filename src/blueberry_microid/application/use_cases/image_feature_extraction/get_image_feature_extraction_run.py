from uuid import UUID

from blueberry_microid.application.dto.image_feature_extraction_dto import ImageFeatureExtractionRunDTO
from blueberry_microid.application.exceptions import ImageFeatureExtractionRunNotFoundError
from blueberry_microid.application.ports.image_feature_extraction_run_repository import (
    ImageFeatureExtractionRunRepositoryPort,
)
from blueberry_microid.application.ports.image_feature_vector_repository import ImageFeatureVectorRepositoryPort


class GetImageFeatureExtractionRunUseCase:
    def __init__(
        self,
        extraction_run_repository: ImageFeatureExtractionRunRepositoryPort,
        feature_vector_repository: ImageFeatureVectorRepositoryPort,
    ) -> None:
        self._extraction_run_repository = extraction_run_repository
        self._feature_vector_repository = feature_vector_repository

    def execute(self, extraction_run_id: UUID) -> ImageFeatureExtractionRunDTO:
        extraction_run = self._extraction_run_repository.get_by_id(extraction_run_id)
        if extraction_run is None:
            raise ImageFeatureExtractionRunNotFoundError(
                f"image_feature_extraction_run '{extraction_run_id}' does not exist"
            )
        vectors = self._feature_vector_repository.list_by_feature_extraction_run_id(extraction_run_id)
        return ImageFeatureExtractionRunDTO.from_entity(extraction_run, vectors)
