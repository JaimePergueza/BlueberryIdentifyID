from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.dataset_curation_run_status import DatasetCurationRunStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DatasetCurationRun:
    """Auditable selection run for human-reviewed two-image analyses.

    This entity stores policy, counts, and metadata only. It does not copy
    images, create dataset releases, train models, or assert taxonomy.
    """

    status: DatasetCurationRunStatus = DatasetCurationRunStatus.COMPLETED
    id: UUID = field(default_factory=uuid4)
    policy: Optional[dict] = None
    total_candidates_scanned: int = 0
    included_count: int = 0
    excluded_count: int = 0
    created_snapshot_id: Optional[UUID] = None
    issues: Optional[list[dict]] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = field(default_factory=_utcnow)

