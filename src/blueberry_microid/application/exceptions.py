"""Use-case level failures.

Distinct from `domain.exceptions`: domain exceptions guard entity invariants
(e.g. an empty sample_code), while these guard orchestration outcomes that
only make sense once a repository or external resource is involved (record
not found, duplicate key, unreadable file).
"""


class ApplicationError(Exception):
    """Base class for all use-case level failures."""


class NotFoundError(ApplicationError):
    """Base class for "referenced record does not exist" failures."""


class SampleNotFoundError(NotFoundError):
    """Raised when a use case references a sample_id that does not exist."""


class PetriImageNotFoundError(NotFoundError):
    """Raised when a use case references a petri_image_id that does not exist."""


class MicroImageNotFoundError(NotFoundError):
    """Raised when a use case references a micro_image_id that does not exist."""


class ModelVersionNotFoundError(NotFoundError):
    """Raised when a use case references a model_version_id that does not exist."""


class AnalysisRunNotFoundError(NotFoundError):
    """Raised when a use case references an analysis_run_id that does not exist."""


class PredictionNotFoundError(NotFoundError):
    """Raised when a use case looks up a Prediction that does not exist yet
    (e.g. the AnalysisRun hasn't been processed, or has none)."""


class HumanReviewNotFoundError(NotFoundError):
    """Raised when a requested HumanReview or final review does not exist."""


class DatasetSnapshotNotFoundError(NotFoundError):
    """Raised when a requested DatasetSnapshot does not exist."""


class DatasetReleaseNotFoundError(NotFoundError):
    """Raised when a requested DatasetRelease does not exist."""


class TrainingPreflightRunNotFoundError(NotFoundError):
    """Raised when a requested TrainingPreflightRun does not exist."""


class TrainingRunNotFoundError(NotFoundError):
    """Raised when a requested TrainingRun does not exist."""


class ImageDatasetAuditRunNotFoundError(NotFoundError):
    """Raised when a requested ImageDatasetAuditRun does not exist."""


class ImageFeatureExtractionRunNotFoundError(NotFoundError):
    """Raised when a requested ImageFeatureExtractionRun does not exist."""


class PetriSegmentationRunNotFoundError(NotFoundError):
    """Raised when a requested PetriSegmentationRun does not exist."""


class ConflictError(ApplicationError):
    """Base class for "the operation conflicts with existing state" failures."""


class DuplicateSampleCodeError(ConflictError):
    """Raised when a sample_code is already registered."""


class DuplicateModelVersionError(ConflictError):
    """Raised when a (name, version) pair is already registered."""


class DuplicatePredictionError(ConflictError):
    """Raised when an AnalysisRun already has a Prediction (1:1 relationship)."""


class DuplicateFinalHumanReviewError(ConflictError):
    """Raised when more than one final HumanReview is attempted for a run."""


class DuplicateDatasetSnapshotError(ConflictError):
    """Raised when a dataset snapshot name/version already exists."""


class DuplicateDatasetItemError(ConflictError):
    """Raised when the same AnalysisRun is inserted twice in one DatasetSnapshot."""


class DuplicateDatasetSplitItemError(ConflictError):
    """Raised when the same DatasetItem is inserted twice in one DatasetRelease."""


class EmptyDatasetSnapshotError(ConflictError):
    """Raised when a DatasetRelease is requested from a DatasetSnapshot that
    has no `included` DatasetItems — there is nothing to split. Mapped to a
    conflict (409), not a validation error: the snapshot reference itself is
    valid, its current contents just cannot satisfy this request yet.
    """


class DatasetSplitMetadataError(ApplicationError):
    """Raised when a `by_lot`/`by_origin_lot` DatasetRelease is requested but
    at least one DatasetItem's Sample is missing the `lot_code` (or
    `origin`) that strategy requires to group by.

    Deliberately fails the whole release rather than silently excluding the
    item or falling back to `by_sample` — either would hide a real
    data-leakage risk instead of surfacing it. Mapped to 422: the request
    itself is well-formed, but the referenced data cannot satisfy the
    requested split strategy.
    """


class BaselineTrainingNotAllowedError(ConflictError):
    """Raised when a baseline TrainingRun cannot be created from current state."""


class TrainingRunComparisonNotAllowedError(ConflictError):
    """Raised when persisted TrainingRuns cannot be compared safely."""


class ImageFeatureExtractionNotAllowedError(ConflictError):
    """Raised when an ImageFeatureExtractionRun cannot be created from the
    current state: the referenced ImageDatasetAuditRun does not exist,
    belongs to a different DatasetRelease, or has a status the requested
    ImageFeatureExtractionConfig does not accept (failed audits are never
    accepted, regardless of config)."""


class PetriSegmentationNotAllowedError(ConflictError):
    """Raised when a PetriSegmentationRun cannot be created from current
    state: the optional image audit is missing, belongs to a different release,
    or has failed."""


class AnalysisRunNotReviewableError(ConflictError):
    """Raised when an AnalysisRun is not in a state that permits review."""


class InvalidImageError(ApplicationError):
    """Raised when an uploaded file fails image validation (empty, wrong mime,
    wrong extension, an unreadable/corrupted image, or a real format that
    does not match the declared MIME type/extension)."""


class ImageTooLargeError(ApplicationError):
    """Raised when an uploaded image exceeds `Settings.max_upload_size_mb`.

    Deliberately not a subclass of `InvalidImageError`: it maps to HTTP 413
    ("Payload Too Large"), not 400 — the file may otherwise be perfectly
    valid, it is simply larger than this deployment currently accepts.
    """


class InvalidModelTypeError(ApplicationError):
    """Raised when a requested model_type is not one of mock/pytorch/external."""


class ImageStorageError(ApplicationError):
    """Raised when persisting image bytes to the storage backend fails."""


class ImageStorageCompensationError(ApplicationError):
    """Raised when a repository write fails AFTER an image was already saved,
    and the compensating delete of that orphaned file also fails.

    The original persistence error is preserved as `__cause__` — this
    exception adds the cleanup failure without hiding it.
    """


class AnalysisRunFinalizationError(ApplicationError):
    """Raised when processing an AnalysisRun fails AND the fallback attempt
    to persist it as `failed` (with an error_message) also fails.

    This is the "doomsday" path of `ProcessAnalysisRunUseCase`: the
    AnalysisRun may be left in `processing` in the database despite the
    in-memory entity having been moved to `failed`. Both the original
    failure and the persistence failure are logged server-side (the latter
    at CRITICAL level); the client only ever sees this generic, controlled
    error, never a raw stack trace. The original error is preserved as
    `__cause__`.
    """


class AnalysisProcessingError(ApplicationError):
    """Raised when processing fails after an AnalysisRun has been claimed.

    `ProcessAnalysisRunUseCase` raises this only after it has made a
    best-effort attempt to persist the AnalysisRun as `failed` with a safe,
    controlled `error_message`. The original exception is preserved as
    `__cause__` and logged server-side; clients receive only a generic 500.
    """
