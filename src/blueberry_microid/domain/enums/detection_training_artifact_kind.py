from enum import Enum


class DetectionTrainingArtifactKind(str, Enum):
    """What a DetectionTrainingArtifactRecord represents.

    `planned_*` values describe paths that would be produced by a future
    real training run and are never backed by real files. `actual_*`
    values are reserved for a future phase and are blocked by default.
    """

    PLANNED_WEIGHTS = "planned_weights"
    PLANNED_METRICS = "planned_metrics"
    PLANNED_PREDICTIONS = "planned_predictions"
    PLANNED_LOGS = "planned_logs"
    PLANNED_RUN_DIR = "planned_run_dir"
    PLANNED_CONFIG = "planned_config"
    PLANNED_MANIFEST = "planned_manifest"
    ACTUAL_WEIGHTS = "actual_weights"
    ACTUAL_METRICS = "actual_metrics"
    ACTUAL_PREDICTIONS = "actual_predictions"
    ACTUAL_LOGS = "actual_logs"
    ACTUAL_MANIFEST = "actual_manifest"
    OTHER = "other"
