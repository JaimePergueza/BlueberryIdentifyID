from enum import Enum


class DetectionTrainingExecutionMode(str, Enum):
    """Only two modes exist in this phase; neither ever executes training."""

    SCAFFOLD_ONLY = "scaffold_only"
    MANUAL_GATE = "manual_gate"
