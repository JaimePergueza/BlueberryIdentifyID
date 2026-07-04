from enum import Enum


class DetectionTrainingArtifactState(str, Enum):
    PLANNED = "planned"
    REGISTERED = "registered"
    MISSING = "missing"
    FORBIDDEN = "forbidden"
    IGNORED = "ignored"
    DELETED = "deleted"
    UNKNOWN = "unknown"
