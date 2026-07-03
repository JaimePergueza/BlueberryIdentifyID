from enum import Enum


class DetectionTrainingReadinessDecision(str, Enum):
    """A preliminary readiness verdict for a DetectionTrainingRun.

    `ready_for_training` means technically ready for a future experimental
    training phase — it never means scientific validity, sufficiency, or a
    trained model.
    """

    READY_FOR_TRAINING = "ready_for_training"
    NEEDS_MORE_ANNOTATIONS = "needs_more_annotations"
    BLOCKED_BY_QUALITY = "blocked_by_quality"
    BLOCKED_BY_ENVIRONMENT = "blocked_by_environment"
    BLOCKED_BY_CONTRACT = "blocked_by_contract"
    BLOCKED_BY_CONFIGURATION = "blocked_by_configuration"
