from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from blueberry_microid.domain.exceptions.errors import DomainError
from blueberry_microid.domain.value_objects.sample_code import SampleCode


class SampleCreate(BaseModel):
    """Payload to register a new blueberry sample.

    `product` is intentionally not a field here: this system supports
    blueberry only, and `CreateSampleUseCase` fixes it internally. Exposing
    it as an input (even with server-side validation) would let a client
    believe it is a real choice.
    """

    sample_code: str
    lot_code: Optional[str] = None
    origin: Optional[str] = None
    collection_date: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("sample_code")
    @classmethod
    def validate_sample_code(cls, value: str) -> str:
        try:
            return str(SampleCode(value))
        except DomainError as exc:
            raise ValueError(str(exc)) from exc


class SampleRead(BaseModel):
    """Representation of a Sample returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sample_code: str
    product: str
    lot_code: Optional[str]
    origin: Optional[str]
    collection_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
