from enum import Enum


class DetectionTrainingMode(str, Enum):
    """Execution mode of a DetectionTrainingRun.

    Only `dry_run` exists in this phase — no mode ever executes real
    training.
    """

    DRY_RUN = "dry_run"
