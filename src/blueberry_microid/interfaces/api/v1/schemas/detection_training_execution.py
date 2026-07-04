from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.detection_training_execution_decision import DetectionTrainingExecutionDecision
from blueberry_microid.domain.enums.detection_training_execution_issue_severity import (
    DetectionTrainingExecutionIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_execution_mode import DetectionTrainingExecutionMode
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus

_REQUIRED_CONFIRMATION_TEXT = "I understand this will only create a scaffold and will not train a model"


class DetectionTrainingExecutionConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class CreateDetectionTrainingExecutionRunRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detection_training_run_id: UUID
    readiness_report_id: UUID
    environment_spec_id: UUID
    artifact_policy_id: UUID
    config: DetectionTrainingExecutionConfigSchema = DetectionTrainingExecutionConfigSchema()
    created_by: Optional[str] = None
    notes: Optional[str] = None


class DetectionTrainingExecutionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    detection_training_run_id: UUID
    readiness_report_id: UUID
    environment_spec_id: UUID
    artifact_policy_id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    status: DetectionTrainingExecutionStatus
    decision: DetectionTrainingExecutionDecision
    mode: DetectionTrainingExecutionMode
    is_executable: bool
    config: dict
    prerequisite_summary: dict
    repository_safety_summary: dict
    execution_plan: dict
    command_preview: dict
    expected_outputs: dict
    risk_summary: dict
    recommendation_summary: dict
    error_count: int
    warning_count: int
    info_count: int
    created_at: datetime
    completed_at: Optional[datetime]
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]


class DetectionTrainingExecutionIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_run_id: UUID
    severity: DetectionTrainingExecutionIssueSeverity
    code: str
    message: str
    details: Optional[dict]
    created_at: datetime


class DetectionTrainingExecutionRunListResponse(BaseModel):
    execution_runs: list[DetectionTrainingExecutionRunResponse]


class DetectionTrainingExecutionIssueListResponse(BaseModel):
    issues: list[DetectionTrainingExecutionIssueResponse]
