from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_issue_severity import DetectionTrainingIssueSeverity
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus


class DetectionTrainingConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: DetectionTrainingAlgorithm = DetectionTrainingAlgorithm.YOLO_DRY_RUN
    mode: DetectionTrainingMode = DetectionTrainingMode.DRY_RUN
    require_quality_gate_passed: bool = True
    require_dataset_yaml: bool = True
    require_yolo_labels: bool = True
    require_coco_annotations: bool = False
    planned_model_family: str = "yolo"
    planned_model_variant: Optional[str] = None
    image_size: int = Field(default=640, gt=0)
    epochs: int = Field(default=50, gt=0)
    batch_size: int = Field(default=8, gt=0)
    patience: Optional[int] = Field(default=None, gt=0)
    seed: int = 42
    device: str = "cpu"
    workers: int = Field(default=0, ge=0)
    allow_external_weights: bool = False
    pretrained_weights_path: Optional[str] = None
    output_dir: Optional[str] = None
    notes: Optional[str] = None


class CreateDetectionTrainingRunRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annotation_bundle_run_id: UUID
    annotation_quality_gate_run_id: UUID
    config: DetectionTrainingConfigSchema = DetectionTrainingConfigSchema()
    created_by: Optional[str] = None
    notes: Optional[str] = None


class DetectionTrainingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    petri_annotation_export_run_id: UUID
    algorithm: DetectionTrainingAlgorithm
    mode: DetectionTrainingMode
    status: DetectionTrainingStatus
    is_runnable: bool
    config: dict
    training_plan: dict
    command_preview: dict
    dataset_summary: dict
    quality_gate_summary: dict
    expected_outputs: dict
    issue_count: int
    warning_count: int
    error_count: int
    annotation_quality_gate_run_id: Optional[UUID]
    created_at: datetime
    completed_at: Optional[datetime]
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]


class DetectionTrainingIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    detection_training_run_id: UUID
    severity: DetectionTrainingIssueSeverity
    code: str
    message: str
    details: Optional[dict]
    created_at: datetime


class DetectionTrainingRunListResponse(BaseModel):
    detection_training_runs: list[DetectionTrainingRunResponse]


class DetectionTrainingIssueListResponse(BaseModel):
    issues: list[DetectionTrainingIssueResponse]
