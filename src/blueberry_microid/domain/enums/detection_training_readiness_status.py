from enum import Enum


class DetectionTrainingReadinessStatus(str, Enum):
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"
    FAILED = "failed"
