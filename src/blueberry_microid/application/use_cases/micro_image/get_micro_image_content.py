from uuid import UUID

from blueberry_microid.application.dto.stored_image_content_dto import StoredImageContentDTO
from blueberry_microid.application.exceptions import MicroImageNotFoundError
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.stored_image_reader import StoredImageReaderPort


class GetMicroImageContentUseCase:
    def __init__(
        self,
        repository: MicroImageRepositoryPort,
        reader: StoredImageReaderPort,
    ) -> None:
        self._repository = repository
        self._reader = reader

    def execute(self, micro_image_id: UUID) -> StoredImageContentDTO:
        image = self._repository.get_by_id(micro_image_id)
        if image is None:
            raise MicroImageNotFoundError(f"micro_image '{micro_image_id}' does not exist")
        return StoredImageContentDTO(
            content=self._reader.read(image.file_path),
            file_name=image.file_name,
            mime_type=image.mime_type,
        )
