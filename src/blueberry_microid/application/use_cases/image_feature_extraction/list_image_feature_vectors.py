from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.image_feature_extraction_dto import ImageFeatureVectorDTO
from blueberry_microid.application.exceptions import ImageFeatureExtractionRunNotFoundError
from blueberry_microid.application.ports.image_feature_extraction_run_repository import (
    ImageFeatureExtractionRunRepositoryPort,
)
from blueberry_microid.application.ports.image_feature_vector_repository import ImageFeatureVectorRepositoryPort
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_modality import ImageModality


class ListImageFeatureVectorsUseCase:
    def __init__(
        self,
        extraction_run_repository: ImageFeatureExtractionRunRepositoryPort,
        feature_vector_repository: ImageFeatureVectorRepositoryPort,
    ) -> None:
        self._extraction_run_repository = extraction_run_repository
        self._feature_vector_repository = feature_vector_repository

    def execute(
        self,
        feature_extraction_run_id: UUID,
        *,
        modality: Optional[ImageModality] = None,
        split: Optional[DatasetSplit] = None,
    ) -> list[ImageFeatureVectorDTO]:
        extraction_run = self._extraction_run_repository.get_by_id(feature_extraction_run_id)
        if extraction_run is None:
            raise ImageFeatureExtractionRunNotFoundError(
                f"image_feature_extraction_run '{feature_extraction_run_id}' does not exist"
            )

        if modality is not None:
            vectors = self._feature_vector_repository.list_by_feature_extraction_run_id_and_modality(
                feature_extraction_run_id, modality
            )
        elif split is not None:
            vectors = self._feature_vector_repository.list_by_feature_extraction_run_id_and_split(
                feature_extraction_run_id, split
            )
        else:
            vectors = self._feature_vector_repository.list_by_feature_extraction_run_id(feature_extraction_run_id)
        return [ImageFeatureVectorDTO.from_entity(vector) for vector in vectors]
