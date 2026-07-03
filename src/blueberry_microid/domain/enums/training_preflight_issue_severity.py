from enum import Enum


class TrainingPreflightIssueSeverity(str, Enum):
    """Severity for persisted preflight validation findings."""

    ERROR = "error"
    WARNING = "warning"
