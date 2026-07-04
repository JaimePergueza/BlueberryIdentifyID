from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from blueberry_microid.domain.enums.detection_training_artifact_issue_severity import (
    DetectionTrainingArtifactIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_artifact_kind import DetectionTrainingArtifactKind
from blueberry_microid.domain.enums.detection_training_artifact_location_type import (
    DetectionTrainingArtifactLocationType,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_decision import (
    DetectionTrainingArtifactPolicyDecision,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_status import (
    DetectionTrainingArtifactPolicyStatus,
)
from blueberry_microid.domain.enums.detection_training_artifact_state import DetectionTrainingArtifactState


def _default_forbidden_extensions() -> list[str]:
    return [".pt", ".pth", ".onnx", ".h5", ".ckpt", ".pb", ".tflite"]


def _default_allowed_metadata_extensions() -> list[str]:
    return [".json", ".yaml", ".yml", ".txt", ".csv", ".md"]


def _default_required_gitignore_patterns() -> list[str]:
    return ["*.pt", "*.pth", "*.onnx", "*.h5", "*.ckpt", "runs/", "training_outputs/"]


class DetectionTrainingArtifactPolicyConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_root_dir: Optional[str] = None
    require_artifact_root_dir: bool = True
    allow_artifacts_inside_repo: bool = False
    allow_artifacts_outside_repo: bool = True
    allow_external_uri: bool = False
    allowed_external_uri_schemes: list[str] = Field(default_factory=list)
    forbidden_extensions: list[str] = Field(default_factory=_default_forbidden_extensions)
    allowed_metadata_extensions: list[str] = Field(default_factory=_default_allowed_metadata_extensions)
    require_gitignore_rules: bool = True
    required_gitignore_patterns: list[str] = Field(default_factory=_default_required_gitignore_patterns)
    require_checksums_for_actual_artifacts: bool = True
    checksum_algorithm: str = "sha256"
    max_artifact_size_mb: Optional[float] = Field(default=None, ge=0)
    allow_actual_artifact_registration: bool = False
    register_planned_artifacts: bool = True
    register_actual_artifacts: bool = False
    allow_missing_planned_paths: bool = True
    strict_mode: bool = False
    notes: Optional[str] = None


class CreateDetectionTrainingArtifactPolicyRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detection_training_run_id: UUID
    readiness_report_id: UUID
    environment_spec_id: UUID
    config: DetectionTrainingArtifactPolicyConfigSchema = DetectionTrainingArtifactPolicyConfigSchema()
    created_by: Optional[str] = None
    notes: Optional[str] = None


class DetectionTrainingArtifactPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    detection_training_run_id: UUID
    readiness_report_id: UUID
    environment_spec_id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    decision: DetectionTrainingArtifactPolicyDecision
    status: DetectionTrainingArtifactPolicyStatus
    is_policy_ready: bool
    config: dict
    artifact_root_dir: Optional[str]
    planned_output_summary: dict
    storage_policy: dict
    git_policy: dict
    checksum_policy: dict
    registry_summary: dict
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


class DetectionTrainingArtifactRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_policy_id: UUID
    detection_training_run_id: UUID
    artifact_kind: DetectionTrainingArtifactKind
    artifact_state: DetectionTrainingArtifactState
    location_type: DetectionTrainingArtifactLocationType
    artifact_path: Optional[str]
    relative_path: Optional[str]
    external_uri: Optional[str]
    file_extension: Optional[str]
    size_bytes: Optional[int]
    checksum_sha256: Optional[str]
    metadata: Optional[dict]
    created_at: datetime


class DetectionTrainingArtifactIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_policy_id: UUID
    severity: DetectionTrainingArtifactIssueSeverity
    code: str
    message: str
    artifact_path: Optional[str]
    details: Optional[dict]
    created_at: datetime


class DetectionTrainingArtifactPolicyListResponse(BaseModel):
    artifact_policies: list[DetectionTrainingArtifactPolicyResponse]


class DetectionTrainingArtifactRecordListResponse(BaseModel):
    records: list[DetectionTrainingArtifactRecordResponse]


class DetectionTrainingArtifactIssueListResponse(BaseModel):
    issues: list[DetectionTrainingArtifactIssueResponse]
