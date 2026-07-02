from enum import Enum


class AnalysisStatus(str, Enum):
    """Workflow state of an AnalysisRun. These are pipeline states, not microbiological classes."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
