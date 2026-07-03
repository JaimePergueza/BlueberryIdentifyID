"""Centralized translation of domain/application exceptions to HTTP responses.

Response body shape for every error handled here::

    {"error": {"code": "sample_not_found", "message": "..."}}

This is separate from FastAPI's own default handling of `RequestValidationError`
(basic request-shape validation, e.g. a missing required field) and
`HTTPException`, which keep FastAPI's default `{"detail": ...}` shape — this
module only concerns itself with exceptions raised by the application/domain
layers once a request has already been parsed successfully.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from blueberry_microid.application.exceptions import (
    AnalysisProcessingError,
    AnalysisRunFinalizationError,
    AnalysisRunNotFoundError,
    AnalysisRunNotReviewableError,
    ApplicationError,
    BaselineTrainingNotAllowedError,
    ConflictError,
    DatasetReleaseNotFoundError,
    DatasetSnapshotNotFoundError,
    DatasetSplitMetadataError,
    DuplicateDatasetItemError,
    DuplicateDatasetSnapshotError,
    DuplicateDatasetSplitItemError,
    DuplicateFinalHumanReviewError,
    DuplicateFinalPetriRegionReviewError,
    DuplicateModelVersionError,
    DuplicatePredictionError,
    DuplicateSampleCodeError,
    EmptyDatasetSnapshotError,
    HumanReviewNotFoundError,
    ImageDatasetAuditRunNotFoundError,
    ImageFeatureExtractionNotAllowedError,
    ImageFeatureExtractionRunNotFoundError,
    ImageStorageCompensationError,
    ImageTooLargeError,
    InvalidImageError,
    InvalidModelTypeError,
    MicroImageNotFoundError,
    ModelVersionNotFoundError,
    NotFoundError,
    PetriAnnotationExportNotAllowedError,
    PetriAnnotationExportRunNotFoundError,
    PetriImageNotFoundError,
    PetriRegionReviewNotFoundError,
    PetriSegmentationNotAllowedError,
    PetriSegmentationRegionNotFoundError,
    PetriSegmentationRunNotFoundError,
    PredictionNotFoundError,
    SampleNotFoundError,
    TrainingPreflightRunNotFoundError,
    TrainingRunComparisonNotAllowedError,
    TrainingRunNotFoundError,
)
from blueberry_microid.domain.exceptions.errors import (
    CrossSampleAnalysisError,
    DomainError,
    InvalidAnalysisRunTransitionError,
    InvalidSplitRatiosError,
    MissingCorrectedLabelError,
)

logger = logging.getLogger("blueberry_microid.errors")

_GENERIC_SERVER_ERROR_MESSAGE = "An unexpected error occurred. Please contact support if the problem persists."
_ANALYSIS_PROCESSING_FAILED_MESSAGE = "Analysis processing failed"


def _resolve_error(exc: Exception) -> tuple[int, str]:
    """Map an exception to (http_status_code, machine-readable error code).

    Checked most-specific-first: a concrete subclass (e.g.
    `SampleNotFoundError`) must be matched before its family's generic
    fallback (`NotFoundError`), so callers get the most useful `code`.
    """
    if isinstance(exc, SampleNotFoundError):
        return 404, "sample_not_found"
    if isinstance(exc, PetriImageNotFoundError):
        return 404, "petri_image_not_found"
    if isinstance(exc, MicroImageNotFoundError):
        return 404, "micro_image_not_found"
    if isinstance(exc, ModelVersionNotFoundError):
        return 404, "model_version_not_found"
    if isinstance(exc, AnalysisRunNotFoundError):
        return 404, "analysis_run_not_found"
    if isinstance(exc, HumanReviewNotFoundError):
        return 404, "human_review_not_found"
    if isinstance(exc, DatasetSnapshotNotFoundError):
        return 404, "dataset_snapshot_not_found"
    if isinstance(exc, DatasetReleaseNotFoundError):
        return 404, "dataset_release_not_found"
    if isinstance(exc, TrainingPreflightRunNotFoundError):
        return 404, "training_preflight_run_not_found"
    if isinstance(exc, TrainingRunNotFoundError):
        return 404, "training_run_not_found"
    if isinstance(exc, ImageDatasetAuditRunNotFoundError):
        return 404, "image_dataset_audit_run_not_found"
    if isinstance(exc, ImageFeatureExtractionRunNotFoundError):
        return 404, "image_feature_extraction_run_not_found"
    if isinstance(exc, PetriSegmentationRunNotFoundError):
        return 404, "petri_segmentation_run_not_found"
    if isinstance(exc, PetriSegmentationRegionNotFoundError):
        return 404, "petri_segmentation_region_not_found"
    if isinstance(exc, PetriRegionReviewNotFoundError):
        return 404, "petri_region_review_not_found"
    if isinstance(exc, PetriAnnotationExportRunNotFoundError):
        return 404, "petri_annotation_export_run_not_found"
    if isinstance(exc, PredictionNotFoundError):
        return 404, "prediction_not_found"
    if isinstance(exc, NotFoundError):
        return 404, "not_found"

    if isinstance(exc, DuplicateSampleCodeError):
        return 409, "duplicate_sample_code"
    if isinstance(exc, DuplicateModelVersionError):
        return 409, "duplicate_model_version"
    if isinstance(exc, DuplicatePredictionError):
        return 409, "duplicate_prediction"
    if isinstance(exc, DuplicateFinalHumanReviewError):
        return 409, "duplicate_final_human_review"
    if isinstance(exc, DuplicateFinalPetriRegionReviewError):
        return 409, "duplicate_final_petri_region_review"
    if isinstance(exc, DuplicateDatasetSnapshotError):
        return 409, "duplicate_dataset_snapshot"
    if isinstance(exc, DuplicateDatasetItemError):
        return 409, "duplicate_dataset_item"
    if isinstance(exc, DuplicateDatasetSplitItemError):
        return 409, "duplicate_dataset_split_item"
    if isinstance(exc, EmptyDatasetSnapshotError):
        return 409, "empty_dataset_snapshot"
    if isinstance(exc, BaselineTrainingNotAllowedError):
        return 409, "baseline_training_not_allowed"
    if isinstance(exc, TrainingRunComparisonNotAllowedError):
        return 409, "training_run_comparison_not_allowed"
    if isinstance(exc, ImageFeatureExtractionNotAllowedError):
        return 409, "image_feature_extraction_not_allowed"
    if isinstance(exc, PetriSegmentationNotAllowedError):
        return 409, "petri_segmentation_not_allowed"
    if isinstance(exc, PetriAnnotationExportNotAllowedError):
        return 409, "petri_annotation_export_not_allowed"
    if isinstance(exc, AnalysisRunNotReviewableError):
        return 409, "analysis_run_not_reviewable"
    if isinstance(exc, ConflictError):
        return 409, "conflict"

    if isinstance(exc, InvalidModelTypeError):
        return 422, "invalid_model_type"

    if isinstance(exc, ImageTooLargeError):
        return 413, "image_too_large"
    if isinstance(exc, InvalidImageError):
        return 400, "invalid_image"
    if isinstance(exc, CrossSampleAnalysisError):
        return 400, "image_sample_mismatch"
    if isinstance(exc, MissingCorrectedLabelError):
        return 422, "invalid_human_review"
    if isinstance(exc, InvalidSplitRatiosError):
        return 422, "invalid_split_ratios"
    if isinstance(exc, DatasetSplitMetadataError):
        return 422, "dataset_split_metadata_error"
    # An AnalysisRun that is not `pending` (already processed, or currently
    # `processing`) cannot be processed again — this is the idempotency
    # guard from AnalysisRun.mark_processing(), surfaced as a conflict with
    # the resource's current state, not a client input error.
    if isinstance(exc, InvalidAnalysisRunTransitionError):
        return 409, "analysis_run_not_processable"

    if isinstance(exc, ImageStorageCompensationError):
        return 500, "image_storage_compensation_failed"
    if isinstance(exc, AnalysisProcessingError):
        return 500, "analysis_processing_failed"
    # The AnalysisRun processing failed AND the fallback attempt to persist
    # it as `failed` also failed — a genuine transactional-consistency
    # problem (e.g. a DB outage), not something the client caused or can fix.
    if isinstance(exc, AnalysisRunFinalizationError):
        return 500, "analysis_run_finalization_failed"

    if isinstance(exc, DomainError):
        return 400, "domain_error"
    if isinstance(exc, ApplicationError):
        return 500, "application_error"

    return 500, "internal_error"


async def _handle_exception(request: Request, exc: Exception) -> JSONResponse:
    status_code, code = _resolve_error(exc)
    request_id = getattr(request.state, "request_id", None)

    # 5xx messages are never the raw exception text: str(exc) on
    # ImageStorageCompensationError, for instance, embeds repr()s of two
    # underlying errors that may contain filesystem paths. Anything below
    # 500 (not-found/conflict/validation) is safe to echo — it is a
    # business-rule message the client is meant to see and act on.
    if isinstance(exc, AnalysisProcessingError):
        message = _ANALYSIS_PROCESSING_FAILED_MESSAGE
    elif status_code >= 500:
        message = _GENERIC_SERVER_ERROR_MESSAGE
        # The stack trace is logged server-side only — this is the one
        # place that happens, whether `exc` reached us via the normal
        # per-exception dispatch (a known ApplicationError/DomainError that
        # happens to map to 5xx, e.g. ImageStorageCompensationError) or via
        # the outer ServerErrorMiddleware fallback (a genuine, unanticipated
        # bug). `RequestLoggingMiddleware` logs the request outcome
        # separately and never duplicates this traceback.
    else:
        message = str(exc)

    if status_code >= 500:
        logger.error(
            "unhandled error while processing request",
            extra={"request_id": request_id, "exception_type": type(exc).__name__},
            exc_info=exc,
        )

    response = JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def register_exception_handlers(app: FastAPI) -> None:
    # Starlette treats a handler registered for the bare `Exception` class
    # specially: it becomes the outer ServerErrorMiddleware fallback, which
    # re-raises after responding (by design, so `TestClient(raise_server_
    # exceptions=True)` still surfaces truly unexpected bugs during tests).
    # Registering our two concrete exception *families* separately routes
    # them through the normal per-exception dispatch instead, so known
    # domain/application errors always come back as a clean JSON response.
    app.add_exception_handler(ApplicationError, _handle_exception)
    app.add_exception_handler(DomainError, _handle_exception)
    # Still registered as the last-resort fallback for anything neither of
    # the above catches (a genuine bug), so production traffic never sees a
    # bare traceback — only a generic 500 in our standard JSON shape.
    app.add_exception_handler(Exception, _handle_exception)
