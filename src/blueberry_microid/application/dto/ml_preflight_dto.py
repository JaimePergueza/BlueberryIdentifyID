from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.training_preflight_issue import TrainingPreflightIssue
from blueberry_microid.domain.entities.training_preflight_run import TrainingPreflightRun
from blueberry_microid.domain.enums.training_preflight_issue_severity import TrainingPreflightIssueSeverity
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus
from blueberry_microid.ml.configs.training_config import TrainingConfig


@dataclass(frozen=True, slots=True)
class CreateTrainingPreflightRunRequest:
    dataset_release_id: UUID
    training_config: TrainingConfig
    validate_image_paths: bool = False
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TrainingPreflightIssueDTO:
    id: UUID
    preflight_run_id: UUID
    severity: TrainingPreflightIssueSeverity
    code: str
    message: str
    field: Optional[str]
    item_ref: Optional[str]
    created_at: datetime

    @classmethod
    def from_entity(cls, issue: TrainingPreflightIssue) -> "TrainingPreflightIssueDTO":
        return cls(
            id=issue.id,
            preflight_run_id=issue.preflight_run_id,
            severity=issue.severity,
            code=issue.code,
            message=issue.message,
            field=issue.field,
            item_ref=issue.item_ref,
            created_at=issue.created_at,
        )


@dataclass(frozen=True, slots=True)
class TrainingPreflightRunDTO:
    id: UUID
    dataset_release_id: UUID
    status: TrainingPreflightStatus
    is_valid: bool
    config: dict
    summary: dict
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
    issues: list[TrainingPreflightIssueDTO] = field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        preflight_run: TrainingPreflightRun,
        issues: Optional[list[TrainingPreflightIssue]] = None,
    ) -> "TrainingPreflightRunDTO":
        return cls(
            id=preflight_run.id,
            dataset_release_id=preflight_run.dataset_release_id,
            status=preflight_run.status,
            is_valid=preflight_run.is_valid,
            config=preflight_run.config,
            summary=preflight_run.summary,
            item_count=preflight_run.item_count,
            train_count=preflight_run.train_count,
            validation_count=preflight_run.validation_count,
            test_count=preflight_run.test_count,
            label_counts=preflight_run.label_counts,
            split_counts=preflight_run.split_counts,
            split_label_counts=preflight_run.split_label_counts,
            leakage_checks=preflight_run.leakage_checks,
            recommendation_summary=preflight_run.recommendation_summary,
            created_at=preflight_run.created_at,
            created_by=preflight_run.created_by,
            notes=preflight_run.notes,
            issues=[TrainingPreflightIssueDTO.from_entity(issue) for issue in issues or []],
        )


def training_config_to_dict(training_config: TrainingConfig) -> dict:
    return asdict(training_config)
