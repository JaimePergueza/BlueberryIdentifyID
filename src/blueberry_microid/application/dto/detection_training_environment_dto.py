from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_environment_issue import (
    DetectionTrainingEnvironmentIssue,
)
from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec
from blueberry_microid.domain.enums.detection_training_environment_decision import (
    DetectionTrainingEnvironmentDecision,
)
from blueberry_microid.domain.enums.detection_training_environment_issue_severity import (
    DetectionTrainingEnvironmentIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_environment_status import DetectionTrainingEnvironmentStatus
from blueberry_microid.ml.configs.detection_training_environment_config import DetectionTrainingEnvironmentConfig


@dataclass(frozen=True)
class DetectionTrainingEnvironmentConfigDTO:
    target_python_version: Optional[str] = None
    target_os: Optional[str] = None
    allow_cpu_training: bool = True
    require_gpu: bool = False
    require_cuda: bool = False
    target_cuda_version: Optional[str] = None
    require_ultralytics: bool = False
    target_ultralytics_version: Optional[str] = None
    require_torch: bool = False
    target_torch_version: Optional[str] = None
    allow_dependency_installation: bool = False
    allow_external_weights: bool = False
    pretrained_weights_policy: str = "none"
    pretrained_weights_path: Optional[str] = None
    artifact_output_dir: Optional[str] = None
    allow_artifacts_outside_repo: bool = True
    allow_artifacts_inside_repo: bool = False
    max_expected_artifact_size_mb: Optional[float] = None
    allow_ci_training: bool = False
    allow_local_training: bool = True
    require_manual_confirmation: bool = True
    strict_mode: bool = False
    notes: Optional[str] = None

    def to_config(self) -> DetectionTrainingEnvironmentConfig:
        return DetectionTrainingEnvironmentConfig(**self.__dict__)


@dataclass(frozen=True)
class CreateDetectionTrainingEnvironmentSpecRequest:
    detection_training_run_id: UUID
    readiness_report_id: UUID
    config: DetectionTrainingEnvironmentConfigDTO = DetectionTrainingEnvironmentConfigDTO()
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class DetectionTrainingEnvironmentSpecDTO:
    id: UUID
    detection_training_run_id: UUID
    readiness_report_id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    decision: DetectionTrainingEnvironmentDecision
    status: DetectionTrainingEnvironmentStatus
    is_environment_ready: bool
    config: dict
    detected_environment: dict
    dependency_policy: dict
    hardware_policy: dict
    artifact_policy: dict
    execution_policy: dict
    setup_instructions: dict
    safe_check_summary: dict
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
    def from_entity(cls, spec: DetectionTrainingEnvironmentSpec) -> "DetectionTrainingEnvironmentSpecDTO":
        return cls(**spec.__dict__)


@dataclass(frozen=True)
class DetectionTrainingEnvironmentIssueDTO:
    id: UUID
    environment_spec_id: UUID
    severity: DetectionTrainingEnvironmentIssueSeverity
    code: str
    message: str
    details: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, issue: DetectionTrainingEnvironmentIssue) -> "DetectionTrainingEnvironmentIssueDTO":
        return cls(**issue.__dict__)
