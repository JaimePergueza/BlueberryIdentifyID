from blueberry_microid.application.dto.petri_image_dto import PetriImageDTO, RegisterPetriImageRequest
from blueberry_microid.application.exceptions import ImageStorageCompensationError, SampleNotFoundError
from blueberry_microid.application.ports.image_storage import ImageCategory
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.services.image_intake_service import ImageIntakeService
from blueberry_microid.domain.entities.petri_image import PetriImage


class RegisterPetriImageUseCase:
    """Registers a Petri dish (macro) image for an existing Sample.

    This is never a photograph of the blueberry fruit itself — only the
    Petri dish where growth is observed. `ImageIntakeService` handles
    validation and storage; if the repository write that follows a
    successful save fails, the saved file is deleted so it never becomes an
    orphan (see `_compensate`).
    """

    def __init__(
        self,
        sample_repository: SampleRepositoryPort,
        petri_image_repository: PetriImageRepositoryPort,
        image_intake: ImageIntakeService,
    ) -> None:
        self._sample_repository = sample_repository
        self._petri_image_repository = petri_image_repository
        self._image_intake = image_intake

    def execute(self, request: RegisterPetriImageRequest) -> PetriImageDTO:
        sample = self._sample_repository.get_by_id(request.sample_id)
        if sample is None:
            raise SampleNotFoundError(f"sample '{request.sample_id}' does not exist")

        intake = self._image_intake.validate_and_store(
            category=ImageCategory.PETRI,
            file_name=request.file_name,
            mime_type=request.mime_type,
            declared_file_size_bytes=request.file_size_bytes,
            content=request.content,
        )

        petri_image = PetriImage(
            sample_id=sample.id,
            file_path=intake.file_path,
            file_name=request.file_name,
            mime_type=request.mime_type,
            file_size_bytes=intake.file_size_bytes,
            width=intake.width,
            height=intake.height,
            captured_at=request.captured_at,
            culture_medium=request.culture_medium,
            incubation_temperature_c=request.incubation_temperature_c,
            incubation_time_hours=request.incubation_time_hours,
            seeding_date=request.seeding_date,
            observed_colony_color=request.observed_colony_color,
            observed_colony_shape=request.observed_colony_shape,
            observed_colony_margin=request.observed_colony_margin,
            observed_colony_texture=request.observed_colony_texture,
            notes=request.notes,
        )

        try:
            created = self._petri_image_repository.add(petri_image)
        except Exception as repository_error:
            self._compensate(intake.file_path, repository_error)
            raise

        return PetriImageDTO.from_entity(created)

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
                f"petri_image persistence failed ({repository_error!r}) and the orphaned "
                f"file at '{file_path}' could not be cleaned up ({cleanup_error!r})"
            ) from repository_error
