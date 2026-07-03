from enum import Enum


class DetectionTrainingEnvironmentStatus(str, Enum):
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"
    FAILED = "failed"
