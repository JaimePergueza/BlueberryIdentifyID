from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class TrainingRunResult:
    experiment_name: str
    status: str
    message: str
    output_dir: str
    created_at: datetime = field(default_factory=_utcnow)
    metrics: Optional[dict[str, float]] = None

