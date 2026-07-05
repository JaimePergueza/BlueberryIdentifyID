"""Use case: validate and run preliminary analysis on two uploaded images.

This use case is deliberately stateless at the persistence layer — it does
not create a Sample, PetriImage, MicroImage, AnalysisRun, or Prediction row.
Its purpose is to provide a quick, non-diagnostic preliminary label from two
raw image uploads without requiring any prior sample registration.

Uploaded images are stored in ``upload_storage_dir`` for traceability, but
their paths are never returned to the caller (CLAUDE.md rule: no internal
paths in API responses).

THIS IS NOT REAL IMAGE ANALYSIS.  See PreliminaryTwoImageAnalysisEngine.
"""

import logging

from blueberry_microid.application.dto.two_image_upload_dto import TwoImageUploadRequest, TwoImageUploadResult
from blueberry_microid.application.exceptions import ImageTooLargeError, InvalidImageError
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.image_validator import ImageValidatorPort
from blueberry_microid.ml.inference_engine.preliminary_two_image_analysis_engine import (
    PreliminaryTwoImageAnalysisEngine,
)

logger = logging.getLogger("blueberry_microid.business.analyze_two_uploaded_images")


class AnalyzeTwoUploadedImagesUseCase:
    """Validate two raw image uploads and return a preliminary visual label.

    Validation rules applied (both images must pass):
    - Actual byte count must not exceed ``max_upload_size_bytes`` (→ 413).
    - MIME type, extension, and Pillow-decodable format must all be
      consistent — see ``ImageValidatorPort`` and ``PillowImageValidator``.

    Storage: images are saved to the upload storage directory for
    traceability.  If saving one image succeeds but saving the other fails,
    the first file is deleted before the error is raised, so no orphan files
    are left behind.

    The engine runs after both images are stored successfully; any engine
    failure leaves both files on disk (they remain useful for debugging) and
    propagates as-is — callers should map it to HTTP 500.
    """

    def __init__(
        self,
        image_validator: ImageValidatorPort,
        upload_storage: ImageStoragePort,
        engine: PreliminaryTwoImageAnalysisEngine,
        max_upload_size_bytes: int | None = None,
    ) -> None:
        self._validator = image_validator
        self._storage = upload_storage
        self._engine = engine
        self._max_size = max_upload_size_bytes

    def execute(self, request: TwoImageUploadRequest) -> TwoImageUploadResult:
        self._validate_bytes(request.petri_file_name, request.petri_mime_type, request.petri_content)
        self._validate_bytes(request.micro_file_name, request.micro_mime_type, request.micro_content)

        petri_path = self._storage.save(
            category=ImageCategory.PETRI,
            original_file_name=request.petri_file_name,
            content=request.petri_content,
        )
        try:
            self._storage.save(
                category=ImageCategory.MICRO,
                original_file_name=request.micro_file_name,
                content=request.micro_content,
            )
        except Exception:
            self._storage.delete(petri_path)
            raise

        output = self._engine.analyze(
            petri_image_bytes=request.petri_content,
            micro_image_bytes=request.micro_content,
        )

        logger.info(
            "preliminary_two_image_analysis completed",
            extra={
                "upload_id": output.upload_id,
                "predicted_label": output.predicted_label.value,
            },
        )

        return TwoImageUploadResult(
            upload_id=output.upload_id,
            predicted_label=output.predicted_label,
            confidence_score=output.confidence_score,
            class_probabilities=output.class_probabilities,
            requires_human_review=output.requires_human_review,
            disclaimer=output.disclaimer,
        )

    def _validate_bytes(self, file_name: str, mime_type: str, content: bytes) -> None:
        actual_size = len(content)
        if self._max_size is not None and actual_size > self._max_size:
            raise ImageTooLargeError(
                f"uploaded file '{file_name}' is {actual_size} bytes, which exceeds "
                f"the maximum allowed size of {self._max_size} bytes"
            )
        self._validator.validate(file_name=file_name, mime_type=mime_type, content=content)
