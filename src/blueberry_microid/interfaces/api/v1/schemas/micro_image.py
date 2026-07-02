from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# There is no MicroImageCreate schema: the upload endpoint accepts
# multipart/form-data (a file plus individual form fields), not a single
# JSON body, and the API computes file_size_bytes itself from the uploaded
# bytes — see interfaces/api/v1/routers/micro_images.py.


class MicroImageRead(BaseModel):
    """Representation of a MicroImage returned by the API.

    `observed_structures` is free-text lab observation and must never
    encode a taxonomic identification (species/genus).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sample_id: UUID
    file_path: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    width: Optional[int]
    height: Optional[int]
    captured_at: Optional[datetime]
    magnification: Optional[str]
    microscope_type: Optional[str]
    staining_method: Optional[str]
    preparation_method: Optional[str]
    observed_structures: Optional[str]
    notes: Optional[str]
    created_at: datetime
