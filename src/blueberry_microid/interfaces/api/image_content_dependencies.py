from fastapi import Depends

from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.stored_image_reader import StoredImageReaderPort
from blueberry_microid.application.use_cases.micro_image.get_micro_image_content import (
    GetMicroImageContentUseCase,
)
from blueberry_microid.application.use_cases.petri_image.get_petri_image_content import (
    GetPetriImageContentUseCase,
)
from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.storage.local_stored_image_reader import LocalStoredImageReader
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_micro_image_repository,
    get_petri_image_repository,
    get_settings_dependency,
)


def get_stored_image_reader(
    settings: Settings = Depends(get_settings_dependency),
) -> StoredImageReaderPort:
    return LocalStoredImageReader(
        allowed_roots=(settings.storage_root, settings.upload_storage_path),
    )


def get_petri_image_content_use_case(
    repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    reader: StoredImageReaderPort = Depends(get_stored_image_reader),
) -> GetPetriImageContentUseCase:
    return GetPetriImageContentUseCase(repository, reader)


def get_micro_image_content_use_case(
    repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    reader: StoredImageReaderPort = Depends(get_stored_image_reader),
) -> GetMicroImageContentUseCase:
    return GetMicroImageContentUseCase(repository, reader)
