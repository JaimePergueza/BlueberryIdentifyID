from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_readiness_issue import (
    DetectionTrainingReadinessIssue,
)
from blueberry_microid.domain.entities.detection_training_readiness_report import (
    DetectionTrainingReadinessReport,
)
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_issue_severity import (
    DetectionTrainingReadinessIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus
from blueberry_microid.ml.configs.detection_training_readiness_config import DetectionTrainingReadinessConfig


@dataclass(frozen=True)
class DetectionTrainingReadinessConfigDTO:
    require_detection_training_planned: bool = True
    require_bundle_completed: bool = True
    require_quality_gate_passed: bool = True
    require_dataset_yaml: bool = True
    require_yolo_labels: bool = True
    require_minimum_data: bool = True
    min_total_images: int = 10
    min_total_annotations: int = 10
    min_train_images: int = 5
    min_validation_images: int = 2
    min_test_images: int = 2
    min_train_annotations: int = 5
    min_validation_annotations: int = 2
    min_test_annotations: int = 2
    warn_if_copy_images_disabled: bool = True
    require_training_executor: bool = False
    require_ultralytics_installed: bool = False
    require_torch_installed: bool = False
    require_gpu: bool = False
    allow_cpu_training_future: bool = True
    require_external_weights_policy: bool = False
    allow_external_weights: bool = False
    strict_mode: bool = False

    def to_config(self) -> DetectionTrainingReadinessConfig:
        return DetectionTrainingReadinessConfig(**self.__dict__)


@dataclass(frozen=True)
class CreateDetectionTrainingReadinessReportRequest:
    detection_training_run_id: UUID
    config: DetectionTrainingReadinessConfigDTO = DetectionTrainingReadinessConfigDTO()
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class DetectionTrainingReadinessReportDTO:
    id: UUID
    detection_training_run_id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    petri_annotation_export_run_id: UUID
    decision: DetectionTrainingReadinessDecision
    status: DetectionTrainingReadinessStatus
    is_ready: bool
    config: dict
    data_summary: dict
    split_summary: dict
    quality_summary: dict
    environment_summary: dict
    contract_summary: dict
    risk_summary: dict
    recommendation_summary: dict
    error_count: int
    warning_count: int
    info_count: int
    annotation_quality_gate_run_id: Optional[UUID]
    created_at: datetime
    completed_at: Optional[datetime]
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]

    @classmethod
    def from_entity(cls, report: DetectionTrainingReadinessReport) -> "DetectionTrainingReadinessReportDTO":
        return cls(**report.__dict__)


@dataclass(frozen=True)
class DetectionTrainingReadinessIssueDTO:
    id: UUID
    readiness_report_id: UUID
    severity: DetectionTrainingReadinessIssueSeverity
    code: str
    message: str
    details: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, issue: DetectionTrainingReadinessIssue) -> "DetectionTrainingReadinessIssueDTO":
        return cls(**issue.__dict__)
