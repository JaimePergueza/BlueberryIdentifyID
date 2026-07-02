from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.exceptions.errors import UnsupportedProductError
from blueberry_microid.domain.value_objects.sample_code import SampleCode

SUPPORTED_PRODUCT = "blueberry"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Sample:
    """A blueberry sample submitted for microbiological screening.

    Sample is the aggregation root that PetriImage, MicroImage and
    AnalysisRun records attach to. It never represents the external
    appearance of the fruit itself — only lab evidence (Petri dish growth
    and microscopy) collected from it.
    """

    sample_code: str
    id: UUID = field(default_factory=uuid4)
    product: str = SUPPORTED_PRODUCT
    lot_code: Optional[str] = None
    origin: Optional[str] = None
    collection_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self.sample_code = str(SampleCode(self.sample_code))
        if self.product.strip().lower() != SUPPORTED_PRODUCT:
            raise UnsupportedProductError(
                f"product must be '{SUPPORTED_PRODUCT}', got '{self.product}'"
            )
