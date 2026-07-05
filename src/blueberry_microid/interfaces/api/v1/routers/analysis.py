"""Router for the two-image upload preliminary analysis endpoints (Fase 40.1 / 42).

Endpoints:
- POST /api/v1/analysis/two-image-upload            (Fase 40.1 / 41)
- GET  /api/v1/analysis-runs/{id}/preliminary-result (Fase 40.1 / 42 enriched)
- GET  /api/v1/analysis-runs/{id}/final-result       (Fase 42 — NEW)

All endpoints carry a mandatory disclaimer: results carry no diagnostic or
taxonomic validity.  Human expert review is mandatory before any operational
conclusion is drawn.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from blueberry_microid.application.dto.two_image_upload_dto import TwoImageUploadRequest
from blueberry_microid.application.use_cases.analysis.analyze_two_uploaded_images import (
    AnalyzeTwoUploadedImagesUseCase,
)
from blueberry_microid.application.use_cases.analysis.get_final_analysis_result import (
    GetFinalAnalysisResultUseCase,
)
from blueberry_microid.application.use_cases.analysis.get_preliminary_result_with_review import (
    GetPreliminaryResultWithReviewUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_analyze_two_uploaded_images_use_case,
    get_get_final_analysis_result_use_case,
    get_get_preliminary_result_with_review_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.final_analysis_result import FinalAnalysisResultRead
from blueberry_microid.interfaces.api.v1.schemas.two_image_upload import (
    PreliminaryResultRead,
    TwoImageUploadAnalysisRead,
)

_PRELIMINARY_DISCLAIMER = (
    "PRELIMINARY RESULT — expert review required. "
    "This result was produced by a classical image-processing heuristic (Fase 41). "
    "It does not perform deep learning, has no diagnostic validity, and never "
    "identifies a microorganism species or genus. "
    "Human expert review is mandatory."
)

router = APIRouter(tags=["analysis"])


@router.post(
    "/analysis/two-image-upload",
    response_model=TwoImageUploadAnalysisRead,
    status_code=status.HTTP_201_CREATED,
    summary="Preliminary two-image upload analysis — persisted (non-diagnostic)",
    description=(
        "Upload a Petri dish photograph and a microscopy photograph of the same "
        "sample.  Both images are validated and stored; Sample, PetriImage, "
        "MicroImage, AnalysisRun and Prediction are persisted.  Real DB identifiers "
        "are returned so the AnalysisRun can be retrieved or reviewed later.  "
        "``requires_human_review`` is always ``true`` — all preliminary uploads "
        "require expert review.  "
        "**Results carry no diagnostic or taxonomic validity.**"
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
        explanation=result.explanation,
        feature_summary=result.feature_summary,
        quality_summary=result.quality_summary,
        decision_trace=result.decision_trace,
        warnings=result.warnings,
    )


@router.get(
    "/analysis-runs/{analysis_run_id}/preliminary-result",
    response_model=PreliminaryResultRead,
    summary="Get preliminary result with human review status (non-diagnostic)",
    description=(
        "Retrieve the Prediction produced by a previously processed AnalysisRun, "
        "formatted as a preliminary result.  Includes current human review status "
        "(Fase 42): ``human_review_status``, ``human_review_completed``, "
        "``final_label`` if a review has been submitted.  "
        "The AnalysisRun must have a Prediction; if not, a 404 is returned.  "
        "**Results carry no diagnostic or taxonomic validity.**"
    ),
)
def get_preliminary_result(
    analysis_run_id: UUID,
    use_case: GetPreliminaryResultWithReviewUseCase = Depends(
        get_get_preliminary_result_with_review_use_case
    ),
) -> PreliminaryResultRead:
    dto = use_case.execute(analysis_run_id)
    return PreliminaryResultRead(
        analysis_run_id=str(dto.analysis_run_id),
        predicted_label=dto.predicted_label,
        confidence_score=dto.confidence_score,
        class_probabilities=dto.class_probabilities,
        requires_human_review=dto.requires_human_review,
        technical_observation=dto.technical_observation,
        disclaimer=_PRELIMINARY_DISCLAIMER,
        explanation=dto.explanation,
        feature_summary=dto.feature_summary,
        quality_summary=dto.quality_summary,
        decision_trace=dto.decision_trace,
        warnings=dto.warnings,
        human_review_status=dto.human_review_status,
        human_review_completed=dto.human_review_completed,
        latest_human_review_id=dto.latest_human_review_id,
        latest_human_review_decision=dto.latest_human_review_decision,
        final_label=dto.final_label,
        reviewed_at=dto.reviewed_at,
    )


@router.get(
    "/analysis-runs/{analysis_run_id}/final-result",
    response_model=FinalAnalysisResultRead,
    summary="Get the final analysis result combining automatic prediction and expert review",
    description=(
        "Returns the full view of the analysis result: automatic Prediction "
        "(unchanged from when it was created) plus the current expert HumanReview "
        "(if submitted).  ``final_label`` and ``status`` reflect the expert decision; "
        "they are ``null``/``pending_human_review`` until a review is submitted.  "
        "**Results carry no diagnostic or taxonomic validity.**"
    ),
)
def get_final_result(
    analysis_run_id: UUID,
    use_case: GetFinalAnalysisResultUseCase = Depends(get_get_final_analysis_result_use_case),
) -> FinalAnalysisResultRead:
    dto = use_case.execute(analysis_run_id)
    return FinalAnalysisResultRead(
        analysis_run_id=dto.analysis_run_id,
        sample_id=dto.sample_id,
        prediction_id=dto.prediction_id,
        preliminary_label=dto.preliminary_label,
        confidence_score=dto.confidence_score,
        explanation=dto.explanation,
        feature_summary=dto.feature_summary,
        quality_summary=dto.quality_summary,
        decision_trace=dto.decision_trace,
        automatic_warnings=dto.automatic_warnings,
        human_review_id=dto.human_review_id,
        human_review_decision=dto.human_review_decision,
        corrected_label=dto.corrected_label,
        reviewer_name=dto.reviewer_name,
        human_comments=dto.human_comments,
        reviewed_at=dto.reviewed_at,
        final_label=dto.final_label,
        status=dto.status,
        human_review_completed=dto.human_review_completed,
        requires_human_review=dto.requires_human_review,
        disclaimer=dto.disclaimer,
    )
