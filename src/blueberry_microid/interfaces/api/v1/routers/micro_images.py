from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from blueberry_microid.application.dto.micro_image_dto import RegisterMicroImageRequest
from blueberry_microid.application.use_cases.micro_image.register_micro_image import RegisterMicroImageUseCase
from blueberry_microid.interfaces.api.v1.dependencies import get_register_micro_image_use_case
from blueberry_microid.interfaces.api.v1.schemas.micro_image import MicroImageRead

router = APIRouter(prefix="/samples", tags=["micro-images"])


@router.post(
    "/{sample_id}/micro-images",
    response_model=MicroImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_micro_image(
    sample_id: UUID,
    file: UploadFile = File(..., description="Microscopy photograph of the sample."),
    captured_at: Optional[datetime] = Form(None),
    magnification: Optional[str] = Form(None),
    microscope_type: Optional[str] = Form(None),
    staining_method: Optional[str] = Form(None),
    preparation_method: Optional[str] = Form(None),
    observed_structures: Optional[str] = Form(
        None, description="Free-text morphological notes only — never a taxonomic identification."
    ),
    notes: Optional[str] = Form(None),
    use_case: RegisterMicroImageUseCase = Depends(get_register_micro_image_use_case),
) -> MicroImageRead:
    # The client never sends a size: the API reads the actual bytes and
    # computes file_size_bytes itself (len(content)), which is the only
    # value ImageIntakeService will trust downstream.
    content = await file.read()

    request = RegisterMicroImageRequest(
        sample_id=sample_id,
        file_name=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
        content=content,
        captured_at=captured_at,
        magnification=magnification,
        microscope_type=microscope_type,
        staining_method=staining_method,
        preparation_method=preparation_method,
        observed_structures=observed_structures,
        notes=notes,
    )
    dto = use_case.execute(request)
    return MicroImageRead.model_validate(dto)
