from enum import Enum


class DetectionTrainingExecutionIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
