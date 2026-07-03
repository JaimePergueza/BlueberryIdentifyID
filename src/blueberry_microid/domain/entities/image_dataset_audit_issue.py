from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.image_dataset_audit_issue_severity import ImageDatasetAuditIssueSeverity
from blueberry_microid.domain.enums.image_modality import ImageModality


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ImageDatasetAuditIssue:
    """A single persisted technical finding (error or warning) for one Petri
    or micro image file checked by an ImageDatasetAuditRun."""

    audit_run_id: UUID
    severity: ImageDatasetAuditIssueSeverity
    modality: ImageModality
    code: str
    message: str
    id: UUID = dataclass_field(default_factory=uuid4)
    dataset_item_id: Optional[UUID] = None
    dataset_split_item_id: Optional[UUID] = None
    image_path: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime = dataclass_field(default_factory=_utcnow)
