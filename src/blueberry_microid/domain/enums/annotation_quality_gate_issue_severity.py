from enum import Enum


class AnnotationQualityGateIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
