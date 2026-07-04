from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_artifact_kind import DetectionTrainingArtifactKind
from blueberry_microid.domain.enums.detection_training_artifact_location_type import (
    DetectionTrainingArtifactLocationType,
)
from blueberry_microid.domain.enums.detection_training_artifact_state import DetectionTrainingArtifactState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DetectionTrainingArtifactRecord:
    """One planned (or, in a future phase, actual) artifact location for a
    DetectionTrainingRun.

    Never stores file content, image bytes, model weights, or full label
    sets — only path/metadata bookkeeping. `artifact_state=planned` never
    means the path exists on disk.
    """

    artifact_policy_id: UUID
    detection_training_run_id: UUID
    artifact_kind: DetectionTrainingArtifactKind
    artifact_state: DetectionTrainingArtifactState
    location_type: DetectionTrainingArtifactLocationType
    id: UUID = field(default_factory=uuid4)
    artifact_path: Optional[str] = None
    relative_path: Optional[str] = None
    external_uri: Optional[str] = None
    file_extension: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        DetectionTrainingArtifactKind(self.artifact_kind)
        DetectionTrainingArtifactState(self.artifact_state)
        DetectionTrainingArtifactLocationType(self.location_type)
        if self.size_bytes is not None and self.size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")
