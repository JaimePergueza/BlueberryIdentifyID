from blueberry_microid.application.dto.analysis_run_dto import AnalysisRunDTO, CreateAnalysisRunRequest
from blueberry_microid.application.exceptions import (
    MicroImageNotFoundError,
    ModelVersionNotFoundError,
    PetriImageNotFoundError,
    SampleNotFoundError,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.exceptions.errors import CrossSampleAnalysisError


class CreateAnalysisRunUseCase:
    """Prepares one explicit, pending multimodal analysis run.

    Resolves and cross-checks all four references, then persists an
    AnalysisRun with status `pending`. It never runs inference, never
    creates a Prediction, and never touches Celery — that is Phase 3+.
    """

    def __init__(
        self,
        sample_repository: SampleRepositoryPort,
        petri_image_repository: PetriImageRepositoryPort,
        micro_image_repository: MicroImageRepositoryPort,
        model_version_repository: ModelVersionRepositoryPort,
        analysis_run_repository: AnalysisRunRepositoryPort,
    ) -> None:
        self._sample_repository = sample_repository
        self._petri_image_repository = petri_image_repository
        self._micro_image_repository = micro_image_repository
        self._model_version_repository = model_version_repository
        self._analysis_run_repository = analysis_run_repository

    def execute(self, request: CreateAnalysisRunRequest) -> AnalysisRunDTO:
        sample = self._sample_repository.get_by_id(request.sample_id)
        if sample is None:
            raise SampleNotFoundError(f"sample '{request.sample_id}' does not exist")

        petri_image = self._petri_image_repository.get_by_id(request.petri_image_id)
        if petri_image is None:
            raise PetriImageNotFoundError(f"petri_image '{request.petri_image_id}' does not exist")

        micro_image = self._micro_image_repository.get_by_id(request.micro_image_id)
        if micro_image is None:
            raise MicroImageNotFoundError(f"micro_image '{request.micro_image_id}' does not exist")

        model_version = self._model_version_repository.get_by_id(request.model_version_id)
        if model_version is None:
            raise ModelVersionNotFoundError(f"model_version '{request.model_version_id}' does not exist")

        if petri_image.sample_id != request.sample_id or micro_image.sample_id != request.sample_id:
            raise CrossSampleAnalysisError(
                "petri_image and micro_image must both belong to the requested sample "
                f"(sample_id={request.sample_id}, petri_image.sample_id={petri_image.sample_id}, "
                f"micro_image.sample_id={micro_image.sample_id})"
            )

        analysis_run = AnalysisRun.create(
            petri_image=petri_image,
            micro_image=micro_image,
            model_version_id=model_version.id,
        )
        created = self._analysis_run_repository.add(analysis_run)
        return AnalysisRunDTO.from_entity(created)
