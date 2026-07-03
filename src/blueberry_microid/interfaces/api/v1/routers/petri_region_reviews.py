from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from blueberry_microid.application.dto.petri_region_review_dto import SubmitPetriRegionReviewRequest
from blueberry_microid.application.services.petri_reviewed_annotation_manifest_exporter import (
    PetriReviewedAnnotationManifestExporter,
)
from blueberry_microid.application.use_cases.petri_region_review.get_final_petri_region_review import (
    GetFinalPetriRegionReviewUseCase,
)
from blueberry_microid.application.use_cases.petri_region_review.list_petri_region_reviews import (
    ListPetriRegionReviewsUseCase,
)
from blueberry_microid.application.use_cases.petri_region_review.submit_petri_region_review import (
    SubmitPetriRegionReviewUseCase,
)
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_get_final_petri_region_review_use_case,
    get_list_petri_region_reviews_use_case,
    get_petri_reviewed_annotation_manifest_exporter,
    get_submit_petri_region_review_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.petri_region_review import (
    PetriRegionReviewCreate,
    PetriRegionReviewListResponse,
    PetriRegionReviewRead,
    PetriReviewedAnnotationManifestResponse,
)

router = APIRouter(tags=["petri-region-reviews"])


@router.post(
    "/ml/petri-regions/{region_id}/reviews",
    response_model=PetriRegionReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_petri_region_review(
    region_id: UUID,
    payload: PetriRegionReviewCreate,
    use_case: SubmitPetriRegionReviewUseCase = Depends(get_submit_petri_region_review_use_case),
) -> PetriRegionReviewRead:
    dto = use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region_id,
            decision=payload.decision,
            reviewer_id=payload.reviewer_id,
            reviewer_name=payload.reviewer_name,
            confidence_score=payload.confidence_score,
            is_final=payload.is_final,
            corrected_bbox_x=payload.corrected_bbox_x,
            corrected_bbox_y=payload.corrected_bbox_y,
            corrected_bbox_width=payload.corrected_bbox_width,
            corrected_bbox_height=payload.corrected_bbox_height,
            corrected_notes=payload.corrected_notes,
            review_notes=payload.review_notes,
        )
    )
    return PetriRegionReviewRead.model_validate(dto)


@router.get("/ml/petri-regions/{region_id}/reviews", response_model=PetriRegionReviewListResponse)
def list_petri_region_reviews_for_region(
    region_id: UUID,
    use_case: ListPetriRegionReviewsUseCase = Depends(get_list_petri_region_reviews_use_case),
) -> PetriRegionReviewListResponse:
    reviews = [PetriRegionReviewRead.model_validate(dto) for dto in use_case.by_region(region_id)]
    return PetriRegionReviewListResponse(reviews=reviews)


@router.get("/ml/petri-regions/{region_id}/reviews/final", response_model=PetriRegionReviewRead)
def get_final_petri_region_review(
    region_id: UUID,
    use_case: GetFinalPetriRegionReviewUseCase = Depends(get_get_final_petri_region_review_use_case),
) -> PetriRegionReviewRead:
    return PetriRegionReviewRead.model_validate(use_case.execute(region_id))


@router.get(
    "/ml/petri-segmentations/{segmentation_run_id}/region-reviews",
    response_model=PetriRegionReviewListResponse,
)
def list_petri_region_reviews_for_segmentation_run(
    segmentation_run_id: UUID,
    use_case: ListPetriRegionReviewsUseCase = Depends(get_list_petri_region_reviews_use_case),
) -> PetriRegionReviewListResponse:
    reviews = [
        PetriRegionReviewRead.model_validate(dto) for dto in use_case.by_segmentation_run(segmentation_run_id)
    ]
    return PetriRegionReviewListResponse(reviews=reviews)


@router.get(
    "/datasets/releases/{dataset_release_id}/petri-region-reviews",
    response_model=PetriRegionReviewListResponse,
)
def list_petri_region_reviews_for_dataset_release(
    dataset_release_id: UUID,
    use_case: ListPetriRegionReviewsUseCase = Depends(get_list_petri_region_reviews_use_case),
) -> PetriRegionReviewListResponse:
    reviews = [
        PetriRegionReviewRead.model_validate(dto) for dto in use_case.by_dataset_release(dataset_release_id)
    ]
    return PetriRegionReviewListResponse(reviews=reviews)


@router.get(
    "/ml/petri-segmentations/{segmentation_run_id}/reviewed-annotations-manifest",
    response_model=PetriReviewedAnnotationManifestResponse,
)
def export_reviewed_annotations_manifest(
    segmentation_run_id: UUID,
    include_non_final: bool = Query(default=False),
    exporter: PetriReviewedAnnotationManifestExporter = Depends(get_petri_reviewed_annotation_manifest_exporter),
) -> PetriReviewedAnnotationManifestResponse:
    manifest = exporter.export(segmentation_run_id, include_non_final=include_non_final)
    return PetriReviewedAnnotationManifestResponse.model_validate(manifest)
