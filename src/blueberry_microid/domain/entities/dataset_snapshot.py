from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DatasetSnapshot:
    """Frozen curated dataset version for future training.

    A snapshot records references and review-derived labels only. It never
    copies image bytes, never trains a model, and never treats a mock
    Prediction as ground truth without a final HumanReview.
    """

    name: str
    version: str
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    selection_criteria: Optional[dict] = None
    item_count: int = 0
    label_distribution: Optional[dict[str, int]] = None
    notes: Optional[str] = None

