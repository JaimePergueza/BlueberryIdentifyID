from enum import Enum


class TrainingPreflightStatus(str, Enum):
    """Outcome of a persisted manifest preflight validation."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
