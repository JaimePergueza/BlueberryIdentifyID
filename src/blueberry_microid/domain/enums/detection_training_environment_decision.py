from enum import Enum


class DetectionTrainingEnvironmentDecision(str, Enum):
    """A preliminary environment-readiness verdict for a future real
    training attempt. Never implies training was executed.
    """

    ENVIRONMENT_READY = "environment_ready"
    NEEDS_MANUAL_SETUP = "needs_manual_setup"
    BLOCKED_BY_MISSING_REQUIREMENTS = "blocked_by_missing_requirements"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    BLOCKED_BY_UNSUPPORTED_PLATFORM = "blocked_by_unsupported_platform"
    BLOCKED_BY_STORAGE_POLICY = "blocked_by_storage_policy"
    BLOCKED_BY_DEPENDENCY_POLICY = "blocked_by_dependency_policy"
