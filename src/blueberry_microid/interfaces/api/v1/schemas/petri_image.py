from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# There is no PetriImageCreate schema: the upload endpoint accepts
# multipart/form-data (a file plus individual form fields), not a single
# JSON body, and the API computes file_size_bytes itself from the uploaded
# bytes — see interfaces/api/v1/routers/petri_images.py.


class PetriImageRead(BaseModel):
    """Representation of a PetriImage returned by the API.

    This is the caja Petri (macro) image — never a photograph of the
    blueberry fruit itself.
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
    culture_medium: Optional[str]
    incubation_temperature_c: Optional[float]
    incubation_time_hours: Optional[float]
    seeding_date: Optional[datetime]
    observed_colony_color: Optional[str]
    observed_colony_shape: Optional[str]
    observed_colony_margin: Optional[str]
    observed_colony_texture: Optional[str]
    notes: Optional[str]
    created_at: datetime
