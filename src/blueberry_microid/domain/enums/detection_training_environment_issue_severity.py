from enum import Enum


class DetectionTrainingEnvironmentIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
