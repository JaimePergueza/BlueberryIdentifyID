from enum import Enum


class DetectionTrainingIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
