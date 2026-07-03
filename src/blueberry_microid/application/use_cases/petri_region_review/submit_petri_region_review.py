from blueberry_microid.application.dto.petri_region_review_dto import (
    PetriRegionReviewDTO,
    SubmitPetriRegionReviewRequest,
)
from blueberry_microid.application.exceptions import PetriSegmentationRegionNotFoundError
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.exceptions.errors import InvalidConfidenceScoreError


class SubmitPetriRegionReviewUseCase:
    """Record a human review of a PetriSegmentationRegion candidate.

    Never modifies the original PetriSegmentationRegion, its
    PetriSegmentationRun, the DatasetRelease, or any image file — a
    corrected bounding box, if any, is stored only on the new
    PetriRegionReview row.
    """

    def __init__(
        self,
        region_repository: PetriSegmentationRegionRepositoryPort,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._region_repository = region_repository
        self._unit_of_work = unit_of_work

    def execute(self, request: SubmitPetriRegionReviewRequest) -> PetriRegionReviewDTO:
        region = self._region_repository.get_by_id(request.petri_segmentation_region_id)
        if region is None:
            raise PetriSegmentationRegionNotFoundError(
                f"petri_segmentation_region '{request.petri_segmentation_region_id}' does not exist"
            )

        try:
            review = PetriRegionReview(
                petri_segmentation_region_id=region.id,
                petri_segmentation_run_id=region.segmentation_run_id,
                dataset_release_id=region.dataset_release_id,
                dataset_item_id=region.dataset_item_id,
                dataset_split_item_id=region.dataset_split_item_id,
                decision=request.decision,
                reviewer_id=request.reviewer_id,
                reviewer_name=request.reviewer_name,
                confidence_score=request.confidence_score,
                is_final=request.is_final,
                corrected_bbox_x=request.corrected_bbox_x,
                corrected_bbox_y=request.corrected_bbox_y,
                corrected_bbox_width=request.corrected_bbox_width,
                corrected_bbox_height=request.corrected_bbox_height,
                corrected_notes=request.corrected_notes,
                review_notes=request.review_notes,
            )
        except InvalidConfidenceScoreError as exc:
            raise ValueError(str(exc)) from exc

        with self._unit_of_work as uow:
            if review.is_final:
                uow.petri_region_review_repository.unset_final_for_region(region.id)
            created = uow.petri_region_review_repository.add(review)
            uow.commit()

        return PetriRegionReviewDTO.from_entity(created)
