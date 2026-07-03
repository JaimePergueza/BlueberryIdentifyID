from enum import Enum


class DetectionTrainingStatus(str, Enum):
    """Outcome of planning a DetectionTrainingRun.

    `planned` means a valid dry-run plan was produced; a future phase could
    execute it, but this run itself never trains anything. `blocked` means
    prerequisites (quality gate, dataset files) are missing. `failed` means
    an internal error occurred while planning.
    """

    PLANNED = "planned"
    BLOCKED = "blocked"
    FAILED = "failed"
