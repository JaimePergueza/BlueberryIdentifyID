from enum import Enum


class ReviewDecision(str, Enum):
    """Outcome an expert reviewer records for an AnalysisRun."""

    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    MARKED_INCONCLUSIVE = "marked_inconclusive"
    REJECTED_INVALID_SAMPLE = "rejected_invalid_sample"
