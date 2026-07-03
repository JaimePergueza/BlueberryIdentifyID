from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_issue_severity import (
    DetectionTrainingReadinessIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus


class DetectionTrainingReadinessConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_detection_training_planned: bool = True
    require_bundle_completed: bool = True
    require_quality_gate_passed: bool = True
    require_dataset_yaml: bool = True
    require_yolo_labels: bool = True
    require_minimum_data: bool = True
    min_total_images: int = Field(default=10, ge=0)
    min_total_annotations: int = Field(default=10, ge=0)
    min_train_images: int = Field(default=5, ge=0)
    min_validation_images: int = Field(default=2, ge=0)
    min_test_images: int = Field(default=2, ge=0)
    min_train_annotations: int = Field(default=5, ge=0)
    min_validation_annotations: int = Field(default=2, ge=0)
    min_test_annotations: int = Field(default=2, ge=0)
    warn_if_copy_images_disabled: bool = True
    require_training_executor: bool = False
    require_ultralytics_installed: bool = False
    require_torch_installed: bool = False
    require_gpu: bool = False
    allow_cpu_training_future: bool = True
    require_external_weights_policy: bool = False
    allow_external_weights: bool = False
    strict_mode: bool = False


class CreateDetectionTrainingReadinessReportRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detection_training_run_id: UUID
    config: DetectionTrainingReadinessConfigSchema = DetectionTrainingReadinessConfigSchema()
    created_by: Optional[str] = None
    notes: Optional[str] = None


class DetectionTrainingReadinessReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class DetectionTrainingReadinessIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    readiness_report_id: UUID
    severity: DetectionTrainingReadinessIssueSeverity
    code: str
    message: str
    details: Optional[dict]
    created_at: datetime


class DetectionTrainingReadinessReportListResponse(BaseModel):
    readiness_reports: list[DetectionTrainingReadinessReportResponse]


class DetectionTrainingReadinessIssueListResponse(BaseModel):
    issues: list[DetectionTrainingReadinessIssueResponse]
