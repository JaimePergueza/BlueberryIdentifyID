from enum import Enum


class ModelEvaluationIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
