"""Use case: validate, store, and persistently record a two-image upload analysis.

Fase 40.1: this use case creates real DB entities (Sample, PetriImage,
MicroImage, AnalysisRun, Prediction) from two raw image uploads.  The
AnalysisRun+Prediction write is atomic via UnitOfWork; the Sample/image
persistence uses individual repository commits (MVP trade-off: orphan rows
are possible if the UoW step fails, but they are valid, harmless entities).

THIS IS NOT REAL IMAGE ANALYSIS.  See PreliminaryTwoImageAnalysisEngine.
`requires_human_review` is always ``True`` for results from this endpoint —
all preliminary uploads require expert review regardless of the visual label.
"""

import logging
import uuid

from blueberry_microid.application.dto.two_image_upload_dto import TwoImageUploadRequest, TwoImageUploadResult
from blueberry_microid.application.exceptions import (
    DuplicateModelVersionError,
    ImageStorageCompensationError,
    ImageTooLargeError,
    InvalidImageError,
)
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.image_validator import ImageValidatorPort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.ml.inference_engine.preliminary_two_image_analysis_engine import (
    PreliminaryTwoImageAnalysisEngine,
)

logger = logging.getLogger("blueberry_microid.business.analyze_two_uploaded_images")

_PRELIMINARY_ENGINE_NAME = "PreliminaryTwoImageEngine"
_PRELIMINARY_ENGINE_VERSION = "0.1.0"


class AnalyzeTwoUploadedImagesUseCase:
    """Validate, store, and persistently record two raw image uploads.

    Creates Sample, PetriImage, MicroImage, AnalysisRun, and Prediction
    from a single two-image upload call.  The AnalysisRun+Prediction write
    is atomic (UnitOfWork); earlier persistence steps (Sample, images) are
    committed individually.

    ``requires_human_review`` is forced to ``True`` for every result — all
    preliminary uploads require expert review, regardless of the label.

    Compensation: if micro storage fails, the already-saved petri file is
    deleted before the error propagates (no orphan files).
    """

    def __init__(
        self,
        image_validator: ImageValidatorPort,
        upload_storage: ImageStoragePort,
        engine: PreliminaryTwoImageAnalysisEngine,
        sample_repository: SampleRepositoryPort,
        petri_image_repository: PetriImageRepositoryPort,
        micro_image_repository: MicroImageRepositoryPort,
        model_version_repository: ModelVersionRepositoryPort,
        unit_of_work: UnitOfWorkPort,
        max_upload_size_bytes: int | None = None,
    ) -> None:
        self._validator = image_validator
        self._storage = upload_storage
        self._engine = engine
        self._sample_repo = sample_repository
        self._petri_repo = petri_image_repository
        self._micro_repo = micro_image_repository
        self._mv_repo = model_version_repository
        self._uow = unit_of_work
        self._max_size = max_upload_size_bytes

    def execute(self, request: TwoImageUploadRequest) -> TwoImageUploadResult:
        petri_validation = self._validate_bytes(
            request.petri_file_name, request.petri_mime_type, request.petri_content
        )
        micro_validation = self._validate_bytes(
            request.micro_file_name, request.micro_mime_type, request.micro_content
        )

        petri_path = self._storage.save(
            category=ImageCategory.PETRI,
            original_file_name=request.petri_file_name,
            content=request.petri_content,
        )
        try:
            micro_path = self._storage.save(
                category=ImageCategory.MICRO,
                original_file_name=request.micro_file_name,
                content=request.micro_content,
            )
        except Exception:
            self._storage.delete(petri_path)
            raise

        sample_code = request.sample_code or f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        sample = self._sample_repo.add(
            Sample(sample_code=sample_code, notes=request.notes)
        )

        petri_image = self._petri_repo.add(
            PetriImage(
                sample_id=sample.id,
                file_path=petri_path,
                file_name=request.petri_file_name,
                mime_type=request.petri_mime_type,
                file_size_bytes=len(request.petri_content),
                width=petri_validation.width,
                height=petri_validation.height,
            )
        )

        micro_image = self._micro_repo.add(
            MicroImage(
                sample_id=sample.id,
                file_path=micro_path,
                file_name=request.micro_file_name,
                mime_type=request.micro_mime_type,
                file_size_bytes=len(request.micro_content),
                width=micro_validation.width,
                height=micro_validation.height,
            )
        )

        model_version = self._get_or_create_model_version()

        analysis_run = AnalysisRun.create(
            petri_image=petri_image,
            micro_image=micro_image,
            model_version_id=model_version.id,
        )

        output = self._engine.analyze(
            petri_image_bytes=request.petri_content,
            micro_image_bytes=request.micro_content,
        )

        prediction = Prediction(
            analysis_run_id=analysis_run.id,
            predicted_label=output.predicted_label,
            confidence_score=output.confidence_score,
            class_probabilities=output.class_probabilities,
            technical_observation=output.disclaimer,
            requires_human_review=True,
        )

        with self._uow:
            analysis_run.mark_processing()
            analysis_run.mark_needs_review()
            self._uow.analysis_run_repository.add(analysis_run)
            self._uow.prediction_repository.add(prediction)
            self._uow.commit()

        logger.info(
            "preliminary_two_image_analysis persisted",
            extra={
                "analysis_run_id": str(analysis_run.id),
                "sample_id": str(sample.id),
                "predicted_label": output.predicted_label.value,
            },
        )

        return TwoImageUploadResult(
            analysis_run_id=analysis_run.id,
            sample_id=sample.id,
            petri_image_id=petri_image.id,
            micro_image_id=micro_image.id,
            predicted_label=output.predicted_label,
            confidence_score=output.confidence_score,
            class_probabilities=output.class_probabilities,
            requires_human_review=True,
            disclaimer=output.disclaimer,
        )

    def _validate_bytes(self, file_name: str, mime_type: str, content: bytes):
        actual_size = len(content)
        if self._max_size is not None and actual_size > self._max_size:
            raise ImageTooLargeError(
                f"uploaded file '{file_name}' is {actual_size} bytes, which exceeds "
                f"the maximum allowed size of {self._max_size} bytes"
            )
        return self._validator.validate(file_name=file_name, mime_type=mime_type, content=content)

    def _get_or_create_model_version(self) -> ModelVersion:
        candidate = ModelVersion(
            name=_PRELIMINARY_ENGINE_NAME,
            version=_PRELIMINARY_ENGINE_VERSION,
            model_type=ModelType.MOCK,
            description="Preliminary two-image upload engine (simulated, non-diagnostic).",
        )
        try:
            return self._mv_repo.add(candidate)
        except DuplicateModelVersionError:
            existing = self._mv_repo.list_all()
            return next(
                mv for mv in existing
                if mv.name == _PRELIMINARY_ENGINE_NAME and mv.version == _PRELIMINARY_ENGINE_VERSION
            )
