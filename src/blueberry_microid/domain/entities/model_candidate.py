from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.model_candidate_kind import ModelCandidateKind
from blueberry_microid.domain.enums.model_candidate_status import ModelCandidateStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ModelCandidate:
    candidate_kind: ModelCandidateKind
    status: ModelCandidateStatus
    model_artifact_path: str
    model_artifact_checksum_sha256: str
    model_artifact_size_bytes: int
    id: UUID = field(default_factory=uuid4)
    local_yolo_training_execution_run_id: Optional[UUID] = None
    detection_training_run_id: Optional[UUID] = None
    model_version_id: Optional[UUID] = None
    metrics_artifact_path: Optional[str] = None
    config_artifact_path: Optional[str] = None
    source_summary: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        self.candidate_kind = ModelCandidateKind(self.candidate_kind)
        self.status = ModelCandidateStatus(self.status)
        if self.model_artifact_size_bytes < 0:
            raise ValueError("model_artifact_size_bytes cannot be negative")
        if not self.model_artifact_path:
            raise ValueError("model_artifact_path is required")
        if not self.model_artifact_checksum_sha256:
            raise ValueError("model_artifact_checksum_sha256 is required")
