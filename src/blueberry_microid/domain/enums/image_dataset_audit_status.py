from enum import Enum


class ImageDatasetAuditStatus(str, Enum):
    """Outcome of a persisted technical image audit for a DatasetRelease."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
