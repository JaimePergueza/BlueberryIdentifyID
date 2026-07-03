from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from blueberry_microid.domain.enums.training_preflight_issue_severity import TrainingPreflightIssueSeverity
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus


class TrainingConfigRequest(BaseModel):
    experiment_name: str
    output_dir: str
    model_family: str = "mock_baseline"
    fusion_strategy: str = "late_fusion"
    dataset_manifest_path: Optional[str] = None
    petri_input_enabled: bool = True
    micro_input_enabled: bool = True
    batch_size: int = 8
    max_epochs: int = 1
    learning_rate: float = 0.001
    random_seed: int = 42
    num_workers: int = 0
    require_lot_aware_split: bool = False
    min_total_items: int = 1
    min_items_per_split: int = 1
    min_items_per_class: int = 1
    allow_inconclusive: bool = False


class CreateTrainingPreflightRunRequestBody(BaseModel):
    dataset_release_id: UUID
    training_config: TrainingConfigRequest
    validate_image_paths: bool = False
    created_by: Optional[str] = None
    notes: Optional[str] = None


class TrainingPreflightIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    preflight_run_id: UUID
    severity: TrainingPreflightIssueSeverity
    code: str
    message: str
    field: Optional[str]
    item_ref: Optional[str]
    created_at: datetime


class TrainingPreflightRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_release_id: UUID
    status: TrainingPreflightStatus
    is_valid: bool
    config: dict[str, Any]
    summary: dict[str, Any]
    item_count: int
    train_count: int
    validation_count: int
    test_count: int
    label_counts: dict[str, int]
    split_counts: dict[str, int]
    split_label_counts: dict[str, dict[str, int]]
    leakage_checks: dict[str, bool]
    recommendation_summary: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    issues: list[TrainingPreflightIssueResponse] = Field(default_factory=list)
