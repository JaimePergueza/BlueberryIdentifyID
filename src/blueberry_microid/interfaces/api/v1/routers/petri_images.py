from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from blueberry_microid.application.dto.petri_image_dto import RegisterPetriImageRequest
from blueberry_microid.application.use_cases.petri_image.register_petri_image import RegisterPetriImageUseCase
from blueberry_microid.interfaces.api.v1.dependencies import get_register_petri_image_use_case
from blueberry_microid.interfaces.api.v1.schemas.petri_image import PetriImageRead

router = APIRouter(prefix="/samples", tags=["petri-images"])


@router.post(
    "/{sample_id}/petri-images",
    response_model=PetriImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_petri_image(
    sample_id: UUID,
    file: UploadFile = File(..., description="Petri dish (macro) photograph — never a photo of the fruit itself."),
    captured_at: Optional[datetime] = Form(None),
    culture_medium: Optional[str] = Form(None),
    incubation_temperature_c: Optional[float] = Form(None),
    incubation_time_hours: Optional[float] = Form(None),
    seeding_date: Optional[datetime] = Form(None),
    observed_colony_color: Optional[str] = Form(None),
    observed_colony_shape: Optional[str] = Form(None),
    observed_colony_margin: Optional[str] = Form(None),
    observed_colony_texture: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    use_case: RegisterPetriImageUseCase = Depends(get_register_petri_image_use_case),
) -> PetriImageRead:
    # The client never sends a size: the API reads the actual bytes and
    # computes file_size_bytes itself (len(content)), which is the only
    # value ImageIntakeService will trust downstream.
    content = await file.read()

    request = RegisterPetriImageRequest(
        sample_id=sample_id,
        file_name=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
        content=content,
        captured_at=captured_at,
        culture_medium=culture_medium,
        incubation_temperature_c=incubation_temperature_c,
        incubation_time_hours=incubation_time_hours,
        seeding_date=seeding_date,
        observed_colony_color=observed_colony_color,
        observed_colony_shape=observed_colony_shape,
        observed_colony_margin=observed_colony_margin,
        observed_colony_texture=observed_colony_texture,
        notes=notes,
    )
    dto = use_case.execute(request)
    return PetriImageRead.model_validate(dto)
