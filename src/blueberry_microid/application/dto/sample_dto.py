from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.sample import Sample


@dataclass(frozen=True, slots=True)
class CreateSampleRequest:
    """Input for CreateSampleUseCase. `product` is not accepted here: the
    system currently supports blueberry only, so it is fixed by the use case.
    """

    sample_code: str
    lot_code: Optional[str] = None
    origin: Optional[str] = None
    collection_date: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class SampleDTO:
    """Output representation of a Sample, decoupled from the ORM model."""

    id: UUID
    sample_code: str
    product: str
    lot_code: Optional[str]
    origin: Optional[str]
    collection_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, sample: Sample) -> "SampleDTO":
        return cls(
            id=sample.id,
            sample_code=sample.sample_code,
            product=sample.product,
            lot_code=sample.lot_code,
            origin=sample.origin,
            collection_date=sample.collection_date,
            notes=sample.notes,
            created_at=sample.created_at,
            updated_at=sample.updated_at,
        )
