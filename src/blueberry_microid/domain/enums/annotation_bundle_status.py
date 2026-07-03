from enum import Enum


class AnnotationBundleStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    DRY_RUN = "dry_run"
