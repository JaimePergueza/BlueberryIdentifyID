from blueberry_microid.application.dto.micro_image_dto import MicroImageDTO, RegisterMicroImageRequest
from blueberry_microid.application.exceptions import ImageStorageCompensationError, SampleNotFoundError
from blueberry_microid.application.ports.image_storage import ImageCategory
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.services.image_intake_service import ImageIntakeService
from blueberry_microid.domain.entities.micro_image import MicroImage


class RegisterMicroImageUseCase:
    """Registers a microscopy image for an existing Sample.

    `observed_structures` and `notes` are free-text lab observations and
    must never encode a taxonomic identification (species/genus). Storage
    and validation go through `ImageIntakeService`; if the repository write
    that follows a successful save fails, the saved file is deleted so it
    never becomes an orphan (see `_compensate`).
    """

    def __init__(
        self,
        sample_repository: SampleRepositoryPort,
        micro_image_repository: MicroImageRepositoryPort,
        image_intake: ImageIntakeService,
    ) -> None:
        self._sample_repository = sample_repository
        self._micro_image_repository = micro_image_repository
        self._image_intake = image_intake

    def execute(self, request: RegisterMicroImageRequest) -> MicroImageDTO:
        sample = self._sample_repository.get_by_id(request.sample_id)
        if sample is None:
            raise SampleNotFoundError(f"sample '{request.sample_id}' does not exist")

        intake = self._image_intake.validate_and_store(
            category=ImageCategory.MICRO,
            file_name=request.file_name,
            mime_type=request.mime_type,
            declared_file_size_bytes=request.file_size_bytes,
            content=request.content,
        )

        micro_image = MicroImage(
            sample_id=sample.id,
            file_path=intake.file_path,
            file_name=request.file_name,
            mime_type=request.mime_type,
            file_size_bytes=intake.file_size_bytes,
            width=intake.width,
            height=intake.height,
            captured_at=request.captured_at,
            magnification=request.magnification,
            microscope_type=request.microscope_type,
            staining_method=request.staining_method,
            preparation_method=request.preparation_method,
            observed_structures=request.observed_structures,
            notes=request.notes,
        )

        try:
            created = self._micro_image_repository.add(micro_image)
        except Exception as repository_error:
            self._compensate(intake.file_path, repository_error)
            raise

        return MicroImageDTO.from_entity(created)

    def _compensate(self, file_path: str, repository_error: Exception) -> None:
        """Delete the just-saved file so a failed persist never leaves an orphan.

        Broad `except Exception` is deliberate: any repository failure (not
        just a specific error type) must trigger cleanup, and we still
        re-raise the original error afterwards — this never hides it.
        """
        try:
            self._image_intake.cleanup(file_path)
        except Exception as cleanup_error:
            raise ImageStorageCompensationError(
                f"micro_image persistence failed ({repository_error!r}) and the orphaned "
                f"file at '{file_path}' could not be cleaned up ({cleanup_error!r})"
            ) from repository_error
