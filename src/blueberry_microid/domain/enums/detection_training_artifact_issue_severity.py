from enum import Enum


class DetectionTrainingArtifactIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
