from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_issue import DetectionTrainingIssue
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_issue_severity import DetectionTrainingIssueSeverity
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_config import DetectionTrainingConfig


@dataclass(frozen=True)
class DetectionTrainingConfigDTO:
    algorithm: DetectionTrainingAlgorithm = DetectionTrainingAlgorithm.YOLO_DRY_RUN
    mode: DetectionTrainingMode = DetectionTrainingMode.DRY_RUN
    require_quality_gate_passed: bool = True
    require_dataset_yaml: bool = True
    require_yolo_labels: bool = True
    require_coco_annotations: bool = False
    planned_model_family: str = "yolo"
    planned_model_variant: Optional[str] = None
    image_size: int = 640
    epochs: int = 50
    batch_size: int = 8
    patience: Optional[int] = None
    seed: int = 42
    device: str = "cpu"
    workers: int = 0
    allow_external_weights: bool = False
    pretrained_weights_path: Optional[str] = None
    output_dir: Optional[str] = None
    notes: Optional[str] = None

    def to_config(self) -> DetectionTrainingConfig:
        return DetectionTrainingConfig(**self.__dict__)


@dataclass(frozen=True)
class CreateDetectionTrainingRunRequest:
    annotation_bundle_run_id: UUID
    annotation_quality_gate_run_id: UUID
    config: DetectionTrainingConfigDTO = DetectionTrainingConfigDTO()
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class DetectionTrainingRunDTO:
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

    @classmethod
    def from_entity(cls, run: DetectionTrainingRun) -> "DetectionTrainingRunDTO":
        return cls(**run.__dict__)


@dataclass(frozen=True)
class DetectionTrainingIssueDTO:
    id: UUID
    detection_training_run_id: UUID
    severity: DetectionTrainingIssueSeverity
    code: str
    message: str
    details: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, issue: DetectionTrainingIssue) -> "DetectionTrainingIssueDTO":
        return cls(**issue.__dict__)
