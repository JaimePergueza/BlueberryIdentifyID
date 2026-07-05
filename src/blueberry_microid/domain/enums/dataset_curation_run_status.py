from enum import Enum


class DatasetCurationRunStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"

