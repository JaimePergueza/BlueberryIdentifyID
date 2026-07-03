from enum import Enum


class DetectionTrainingAlgorithm(str, Enum):
    """A detector algorithm family a future training run might plan for.

    Only a dry-run planning value exists in this phase. Real training
    (`yolo_train`) is deliberately not defined yet.
    """

    YOLO_DRY_RUN = "yolo_dry_run"
