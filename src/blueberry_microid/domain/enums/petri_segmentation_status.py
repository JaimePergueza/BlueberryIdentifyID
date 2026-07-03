from enum import Enum


class PetriSegmentationStatus(str, Enum):
    """Operational status of a classical Petri segmentation run."""

    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
