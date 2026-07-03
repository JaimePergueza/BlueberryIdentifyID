from enum import Enum


class ImageDatasetAuditIssueSeverity(str, Enum):
    """Severity for a persisted image audit finding."""

    ERROR = "error"
    WARNING = "warning"
