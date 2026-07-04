from enum import Enum


class DetectionTrainingArtifactPolicyDecision(str, Enum):
    """A preliminary artifact-policy verdict for a future real training
    attempt. Never implies any artifact was actually created.
    """

    ARTIFACT_POLICY_READY = "artifact_policy_ready"
    NEEDS_EXTERNAL_STORAGE = "needs_external_storage"
    BLOCKED_BY_REPO_STORAGE = "blocked_by_repo_storage"
    BLOCKED_BY_MISSING_OUTPUT_DIR = "blocked_by_missing_output_dir"
    BLOCKED_BY_FORBIDDEN_EXTENSION = "blocked_by_forbidden_extension"
    BLOCKED_BY_POLICY_VIOLATION = "blocked_by_policy_violation"
    BLOCKED_BY_ENVIRONMENT = "blocked_by_environment"
