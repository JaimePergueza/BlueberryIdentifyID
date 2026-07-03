from enum import Enum


class ImageFeatureExtractionStatus(str, Enum):
    """Outcome of a persisted non-deep feature extraction run.

    Not a model-training status: extraction never fits/trains anything.
    """

    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
