from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.model_type import ModelType


class ModelVersionCreate(BaseModel):
    """Payload to register a new inference engine version (e.g. the mock engine)."""

    name: str
    version: str
    model_type: ModelType
    description: Optional[str] = None
    is_active: bool = True


class ModelVersionRead(BaseModel):
    """Representation of a ModelVersion returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    model_type: ModelType
    description: Optional[str]
    is_active: bool
    created_at: datetime
