from enum import Enum


class DetectionTrainingExecutionDecision(str, Enum):
    """Preliminary verdict for a future manual training execution attempt.

    Never implies a training command was executed or a model was trained.
    """

    BLOCKED_BY_PREREQUISITES = "blocked_by_prerequisites"
    BLOCKED_BY_CI = "blocked_by_ci"
    BLOCKED_BY_REPOSITORY_SAFETY = "blocked_by_repository_safety"
    BLOCKED_BY_ARTIFACT_POLICY = "blocked_by_artifact_policy"
    BLOCKED_BY_ENVIRONMENT = "blocked_by_environment"
    BLOCKED_BY_READINESS = "blocked_by_readiness"
    BLOCKED_BY_CONFIGURATION = "blocked_by_configuration"
    MANUAL_CONFIRMATION_REQUIRED = "manual_confirmation_required"
    READY_FOR_MANUAL_EXECUTION = "ready_for_manual_execution"
