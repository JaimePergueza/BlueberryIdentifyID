from enum import Enum


class DetectionTrainingReadinessIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
