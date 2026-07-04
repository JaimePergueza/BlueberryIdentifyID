from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from blueberry_microid.domain.enums.detection_training_execution_mode import DetectionTrainingExecutionMode

_REQUIRED_CONFIRMATION_TEXT = "I understand this will only create a scaffold and will not train a model"


@dataclass(frozen=True)
class DetectionTrainingExecutionConfig:
    """Policy for gating a future, manually-triggered real training attempt.

    `enable_real_training` and `dry_run_only` are safety rails, not feature
    flags: this phase never executes a training command regardless of their
    value — `enable_real_training=true` or `dry_run_only=false` always block
    (`training_execution_disabled`), they never unlock execution.
    """

    mode: DetectionTrainingExecutionMode = DetectionTrainingExecutionMode.SCAFFOLD_ONLY
    enable_real_training: bool = False
    require_manual_confirmation: bool = True
    manual_confirmation_text: Optional[str] = None
    required_confirmation_text: str = _REQUIRED_CONFIRMATION_TEXT
    block_in_ci: bool = True
    require_detection_training_planned: bool = True
    require_readiness_ready: bool = True
    require_environment_ready: bool = True
    require_artifact_policy_ready: bool = True
    require_repository_safety_passed: bool = True
    require_command_preview: bool = True
    require_expected_outputs: bool = True
    allow_ready_to_execute_status: bool = False
    allow_manual_gate_status: bool = True
    dry_run_only: bool = True
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        DetectionTrainingExecutionMode(self.mode)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value if isinstance(self.mode, DetectionTrainingExecutionMode) else self.mode,
            "enable_real_training": self.enable_real_training,
            "require_manual_confirmation": self.require_manual_confirmation,
            "manual_confirmation_text": self.manual_confirmation_text,
            "required_confirmation_text": self.required_confirmation_text,
            "block_in_ci": self.block_in_ci,
            "require_detection_training_planned": self.require_detection_training_planned,
            "require_readiness_ready": self.require_readiness_ready,
            "require_environment_ready": self.require_environment_ready,
            "require_artifact_policy_ready": self.require_artifact_policy_ready,
            "require_repository_safety_passed": self.require_repository_safety_passed,
            "require_command_preview": self.require_command_preview,
            "require_expected_outputs": self.require_expected_outputs,
            "allow_ready_to_execute_status": self.allow_ready_to_execute_status,
            "allow_manual_gate_status": self.allow_manual_gate_status,
            "dry_run_only": self.dry_run_only,
            "created_by": self.created_by,
            "notes": self.notes,
        }
