from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from blueberry_microid.application.dto.stored_image_content_dto import StoredImageContentDTO
from blueberry_microid.application.use_cases.micro_image.get_micro_image_content import (
    GetMicroImageContentUseCase,
)
from blueberry_microid.application.use_cases.petri_image.get_petri_image_content import (
    GetPetriImageContentUseCase,
)
from blueberry_microid.interfaces.api.image_content_dependencies import (
    get_micro_image_content_use_case,
    get_petri_image_content_use_case,
)

router = APIRouter(tags=["image-content"])


def _response(payload: StoredImageContentDTO) -> Response:
    safe_name = Path(payload.file_name).name.replace('"', "") or "image"
    return Response(
        content=payload.content,
        media_type=payload.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/petri-images/{petri_image_id}/content", response_class=Response)
def get_petri_image_content(
    petri_image_id: UUID,
    use_case: GetPetriImageContentUseCase = Depends(get_petri_image_content_use_case),
) -> Response:
    return _response(use_case.execute(petri_image_id))


@router.get("/micro-images/{micro_image_id}/content", response_class=Response)
def get_micro_image_content(
    micro_image_id: UUID,
    use_case: GetMicroImageContentUseCase = Depends(get_micro_image_content_use_case),
) -> Response:
    return _response(use_case.execute(micro_image_id))
