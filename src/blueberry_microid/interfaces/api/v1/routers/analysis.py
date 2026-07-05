"""Router for the two-image upload preliminary analysis endpoint (Fase 40.1).

Endpoints:
- POST /api/v1/analysis/two-image-upload
- GET  /api/v1/analysis-runs/{analysis_run_id}/preliminary-result

Both carry a mandatory disclaimer: results are produced by a mock engine
and carry no diagnostic or taxonomic validity.

Fase 40.1: the POST endpoint now persists Sample, PetriImage, MicroImage,
AnalysisRun and Prediction; the response includes real DB identifiers.
`requires_human_review` is always True for this endpoint.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from blueberry_microid.application.dto.two_image_upload_dto import TwoImageUploadRequest
from blueberry_microid.application.use_cases.analysis.analyze_two_uploaded_images import (
    AnalyzeTwoUploadedImagesUseCase,
)
from blueberry_microid.application.use_cases.inference.get_prediction import GetPredictionForAnalysisRunUseCase
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_analyze_two_uploaded_images_use_case,
    get_get_prediction_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.two_image_upload import (
    PreliminaryResultRead,
    TwoImageUploadAnalysisRead,
)

_MOCK_DISCLAIMER = (
    "This result was produced by a simulated (mock) inference engine, for technical "
    "testing only.  It does not perform real image analysis, has no diagnostic "
    "validity, and never identifies a microorganism species or genus."
)

router = APIRouter(tags=["analysis"])


@router.post(
    "/analysis/two-image-upload",
    response_model=TwoImageUploadAnalysisRead,
    status_code=status.HTTP_201_CREATED,
    summary="Preliminary two-image upload analysis — persisted (non-diagnostic, mock engine)",
    description=(
        "Upload a Petri dish photograph and a microscopy photograph of the same "
        "sample.  Both images are validated and stored; Sample, PetriImage, "
        "MicroImage, AnalysisRun and Prediction are persisted.  Real DB identifiers "
        "are returned so the AnalysisRun can be retrieved or reviewed later.  "
        "``requires_human_review`` is always ``true`` — all preliminary uploads "
        "require expert review.  "
        "**This endpoint uses a simulated (mock) inference engine.  Results carry "
        "no diagnostic or taxonomic validity.**"
    ),
)
async def analyze_two_uploaded_images(
    petri_image: UploadFile = File(
        ...,
        description="Petri dish photograph (JPEG/PNG/TIFF). Never a photo of the fruit itself.",
    ),
    micro_image: UploadFile = File(
        ...,
        description="Microscopy photograph taken from the same Petri dish sample.",
    ),
    sample_code: Optional[str] = Form(
        default=None,
        description="Optional lab sample code. Auto-generated if omitted.",
    ),
    notes: Optional[str] = Form(
        default=None,
        description="Optional free-text notes for the sample.",
    ),
    use_case: AnalyzeTwoUploadedImagesUseCase = Depends(get_analyze_two_uploaded_images_use_case),
) -> TwoImageUploadAnalysisRead:
    petri_content = await petri_image.read()
    micro_content = await micro_image.read()

    request = TwoImageUploadRequest(
        petri_file_name=petri_image.filename or "petri_upload",
        petri_mime_type=petri_image.content_type or "application/octet-stream",
        petri_content=petri_content,
        micro_file_name=micro_image.filename or "micro_upload",
        micro_mime_type=micro_image.content_type or "application/octet-stream",
        micro_content=micro_content,
        sample_code=sample_code or None,
        notes=notes or None,
    )
    result = use_case.execute(request)

    return TwoImageUploadAnalysisRead(
        analysis_run_id=result.analysis_run_id,
        prediction_id=result.prediction_id,
        sample_id=result.sample_id,
        petri_image_id=result.petri_image_id,
        micro_image_id=result.micro_image_id,
        predicted_label=result.predicted_label,
        confidence_score=result.confidence_score,
        class_probabilities=result.class_probabilities,
        requires_human_review=result.requires_human_review,
        disclaimer=result.disclaimer,
    )


@router.get(
    "/analysis-runs/{analysis_run_id}/preliminary-result",
    response_model=PreliminaryResultRead,
    summary="Get preliminary result for an existing AnalysisRun (non-diagnostic, mock engine)",
    description=(
        "Retrieve the Prediction produced by a previously processed AnalysisRun, "
        "formatted as a preliminary result.  The AnalysisRun must have status "
        "'completed' or 'needs_review'; if no Prediction exists yet, a 404 is "
        "returned.  "
        "**Results carry no diagnostic or taxonomic validity.**"
    ),
)
def get_preliminary_result(
    analysis_run_id: UUID,
    use_case: GetPredictionForAnalysisRunUseCase = Depends(get_get_prediction_use_case),
) -> PreliminaryResultRead:
    prediction = use_case.execute(analysis_run_id)
    return PreliminaryResultRead(
        analysis_run_id=str(prediction.analysis_run_id),
        predicted_label=prediction.predicted_label,
        confidence_score=prediction.confidence_score,
        class_probabilities=prediction.class_probabilities,
        requires_human_review=prediction.requires_human_review,
        technical_observation=prediction.technical_observation,
        disclaimer=_MOCK_DISCLAIMER,
    )
