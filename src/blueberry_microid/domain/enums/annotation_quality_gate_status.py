from enum import Enum


class AnnotationQualityGateStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
