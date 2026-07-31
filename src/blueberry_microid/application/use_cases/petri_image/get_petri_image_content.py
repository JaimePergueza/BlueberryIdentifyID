from uuid import UUID

from blueberry_microid.application.dto.stored_image_content_dto import StoredImageContentDTO
from blueberry_microid.application.exceptions import PetriImageNotFoundError
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.stored_image_reader import StoredImageReaderPort


class GetPetriImageContentUseCase:
    def __init__(
        self,
        repository: PetriImageRepositoryPort,
        reader: StoredImageReaderPort,
    ) -> None:
        self._repository = repository
        self._reader = reader

    def execute(self, petri_image_id: UUID) -> StoredImageContentDTO:
        image = self._repository.get_by_id(petri_image_id)
        if image is None:
            raise PetriImageNotFoundError(f"petri_image '{petri_image_id}' does not exist")
        return StoredImageContentDTO(
            content=self._reader.read(image.file_path),
            file_name=image.file_name,
            mime_type=image.mime_type,
        )
