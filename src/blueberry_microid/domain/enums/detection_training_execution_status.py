from enum import Enum


class DetectionTrainingExecutionStatus(str, Enum):
    """Status of a DetectionTrainingExecutionRun evaluation.

    There is deliberately no `running`/`completed`/`trained`/`model_created`
    value: this phase never executes a training command.
    """

    BLOCKED = "blocked"
    MANUAL_REQUIRED = "manual_required"
    READY_TO_EXECUTE = "ready_to_execute"
    FAILED = "failed"
