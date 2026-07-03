from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TrainingPreflightRun:
    """Persisted result of validating a DatasetRelease for future training.

    Stores validation metadata only. It never stores image bytes, model
    performance metrics, trained artifacts, or taxonomic claims.
    """

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
    id: UUID = field(default_factory=uuid4)
    recommendation_summary: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status == TrainingPreflightStatus.FAILED and self.is_valid:
            raise ValueError("failed preflight runs must have is_valid=false")
        if self.status in {TrainingPreflightStatus.PASSED, TrainingPreflightStatus.WARNING} and not self.is_valid:
            raise ValueError("passed/warning preflight runs must have is_valid=true")
