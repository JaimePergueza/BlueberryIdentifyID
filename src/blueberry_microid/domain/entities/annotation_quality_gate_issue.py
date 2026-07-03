from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.annotation_quality_gate_issue_severity import (
    AnnotationQualityGateIssueSeverity,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AnnotationQualityGateIssue:
    """One blocking error or non-blocking warning from an annotation quality gate."""

    quality_gate_run_id: UUID
    severity: AnnotationQualityGateIssueSeverity
    code: str
    message: str
    id: UUID = field(default_factory=uuid4)
    split: Optional[str] = None
    image_path: Optional[str] = None
    annotation_ref: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        AnnotationQualityGateIssueSeverity(self.severity)
        if not self.code:
            raise ValueError("code must not be blank")
        if not self.message:
            raise ValueError("message must not be blank")
        if self.split is not None and self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
