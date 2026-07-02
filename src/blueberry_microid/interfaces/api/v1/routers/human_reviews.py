from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.human_review_dto import SubmitHumanReviewRequest
from blueberry_microid.application.use_cases.review.get_final_human_review import GetFinalHumanReviewUseCase
from blueberry_microid.application.use_cases.review.list_human_reviews import ListHumanReviewsUseCase
from blueberry_microid.application.use_cases.review.submit_human_review import SubmitHumanReviewUseCase
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_get_final_human_review_use_case,
    get_list_human_reviews_use_case,
    get_submit_human_review_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.human_review import (
    HumanReviewCreate,
    HumanReviewListResponse,
    HumanReviewRead,
)

router = APIRouter(prefix="/analysis-runs/{analysis_run_id}/reviews", tags=["human-reviews"])


@router.post("", response_model=HumanReviewRead, status_code=status.HTTP_201_CREATED)
def submit_human_review(
    analysis_run_id: UUID,
    payload: HumanReviewCreate,
    use_case: SubmitHumanReviewUseCase = Depends(get_submit_human_review_use_case),
) -> HumanReviewRead:
    request = SubmitHumanReviewRequest(
        analysis_run_id=analysis_run_id,
        reviewer_name=payload.reviewer_name,
        review_decision=payload.review_decision,
        corrected_label=payload.corrected_label,
        comments=payload.comments,
        is_final=payload.is_final,
    )
    dto = use_case.execute(request)
    return HumanReviewRead.model_validate(dto)


@router.get("", response_model=HumanReviewListResponse)
def list_human_reviews(
    analysis_run_id: UUID,
    use_case: ListHumanReviewsUseCase = Depends(get_list_human_reviews_use_case),
) -> HumanReviewListResponse:
    reviews = use_case.execute(analysis_run_id)
    return HumanReviewListResponse(reviews=[HumanReviewRead.model_validate(review) for review in reviews])


@router.get("/final", response_model=HumanReviewRead)
def get_final_human_review(
    analysis_run_id: UUID,
    use_case: GetFinalHumanReviewUseCase = Depends(get_get_final_human_review_use_case),
) -> HumanReviewRead:
    dto = use_case.execute(analysis_run_id)
    return HumanReviewRead.model_validate(dto)
