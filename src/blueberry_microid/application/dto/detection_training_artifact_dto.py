from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_artifact_issue import DetectionTrainingArtifactIssue
from blueberry_microid.domain.entities.detection_training_artifact_policy import DetectionTrainingArtifactPolicy
from blueberry_microid.domain.entities.detection_training_artifact_record import DetectionTrainingArtifactRecord
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
from blueberry_microid.ml.configs.detection_training_artifact_policy_config import (
    DetectionTrainingArtifactPolicyConfig,
)


def _default_forbidden_extensions() -> list[str]:
    return [".pt", ".pth", ".onnx", ".h5", ".ckpt", ".pb", ".tflite"]


def _default_allowed_metadata_extensions() -> list[str]:
    return [".json", ".yaml", ".yml", ".txt", ".csv", ".md"]


def _default_required_gitignore_patterns() -> list[str]:
    return ["*.pt", "*.pth", "*.onnx", "*.h5", "*.ckpt", "runs/", "training_outputs/"]


@dataclass(frozen=True)
class DetectionTrainingArtifactPolicyConfigDTO:
    artifact_root_dir: Optional[str] = None
    require_artifact_root_dir: bool = True
    allow_artifacts_inside_repo: bool = False
    allow_artifacts_outside_repo: bool = True
    allow_external_uri: bool = False
    allowed_external_uri_schemes: list[str] = field(default_factory=list)
    forbidden_extensions: list[str] = field(default_factory=_default_forbidden_extensions)
    allowed_metadata_extensions: list[str] = field(default_factory=_default_allowed_metadata_extensions)
    require_gitignore_rules: bool = True
    required_gitignore_patterns: list[str] = field(default_factory=_default_required_gitignore_patterns)
    require_checksums_for_actual_artifacts: bool = True
    checksum_algorithm: str = "sha256"
    max_artifact_size_mb: Optional[float] = None
    allow_actual_artifact_registration: bool = False
    register_planned_artifacts: bool = True
    register_actual_artifacts: bool = False
    allow_missing_planned_paths: bool = True
    strict_mode: bool = False
    notes: Optional[str] = None

    def to_config(self) -> DetectionTrainingArtifactPolicyConfig:
        return DetectionTrainingArtifactPolicyConfig(**self.__dict__)


@dataclass(frozen=True)
class CreateDetectionTrainingArtifactPolicyRequest:
    detection_training_run_id: UUID
    readiness_report_id: UUID
    environment_spec_id: UUID
    config: DetectionTrainingArtifactPolicyConfigDTO = DetectionTrainingArtifactPolicyConfigDTO()
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class DetectionTrainingArtifactPolicyDTO:
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

    @classmethod
    def from_entity(cls, policy: DetectionTrainingArtifactPolicy) -> "DetectionTrainingArtifactPolicyDTO":
        return cls(**policy.__dict__)


@dataclass(frozen=True)
class DetectionTrainingArtifactRecordDTO:
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

    @classmethod
    def from_entity(cls, record: DetectionTrainingArtifactRecord) -> "DetectionTrainingArtifactRecordDTO":
        return cls(**record.__dict__)


@dataclass(frozen=True)
class DetectionTrainingArtifactIssueDTO:
    id: UUID
    artifact_policy_id: UUID
    severity: DetectionTrainingArtifactIssueSeverity
    code: str
    message: str
    artifact_path: Optional[str]
    details: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, issue: DetectionTrainingArtifactIssue) -> "DetectionTrainingArtifactIssueDTO":
        return cls(**issue.__dict__)
