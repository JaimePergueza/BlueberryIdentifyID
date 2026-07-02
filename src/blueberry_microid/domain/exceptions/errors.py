class DomainError(Exception):
    """Base class for all business-rule violations raised by the domain layer."""


class EmptySampleCodeError(DomainError):
    """Raised when a Sample is created or renamed with a blank sample_code."""


class UnsupportedProductError(DomainError):
    """Raised when a Sample references a product other than blueberry.

    The system currently supports a single product line (blueberry). This is
    a deliberate MVP constraint, not a technical limitation.
    """


class InvalidConfidenceScoreError(DomainError):
    """Raised when a confidence_score falls outside the [0, 1] range."""


class CrossSampleAnalysisError(DomainError):
    """Raised when an AnalysisRun would combine a PetriImage and a MicroImage
    that do not belong to the same Sample.
    """


class MissingCorrectedLabelError(DomainError):
    """Raised when a HumanReview is recorded as `corrected` without a corrected_label."""


class InvalidAnalysisRunTransitionError(DomainError):
    """Raised when an AnalysisRun status transition is attempted from a status
    that does not allow it (e.g. marking as `completed` a run that was never
    `processing`, or reprocessing one that is already `completed`/`failed`/
    `needs_review`). This is the idempotency guard: an AnalysisRun can only
    ever be processed once; a retry requires creating a new AnalysisRun.
    """


class InvalidSplitRatiosError(DomainError):
    """Raised when a DatasetRelease's train/validation/test ratios are
    outside [0, 1] or do not sum to 1.0 (within floating-point tolerance).
    """
