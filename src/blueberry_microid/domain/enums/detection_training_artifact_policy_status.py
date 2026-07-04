from enum import Enum


class DetectionTrainingArtifactPolicyStatus(str, Enum):
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"
    FAILED = "failed"
