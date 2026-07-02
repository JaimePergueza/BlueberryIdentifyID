from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.model_type import ModelType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ModelVersion:
    """A registered, traceable version of an inference engine.

    Exists even while the engine is a simulated/mock implementation, so every
    Prediction can always point to the exact model that produced it.
    """

    name: str
    version: str
    model_type: ModelType
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)
