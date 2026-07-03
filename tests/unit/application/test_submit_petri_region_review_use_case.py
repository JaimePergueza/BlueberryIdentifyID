from uuid import uuid4

import pytest

from blueberry_microid.application.dto.petri_region_review_dto import SubmitPetriRegionReviewRequest
from blueberry_microid.application.exceptions import PetriSegmentationRegionNotFoundError
from blueberry_microid.application.use_cases.petri_region_review.submit_petri_region_review import (
    SubmitPetriRegionReviewUseCase,
)
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_region_review_decision import PetriRegionReviewDecision
from tests.unit.application.fakes import (
    FailingAddPetriRegionReviewRepository,
    FakeUnitOfWork,
    InMemoryPetriRegionReviewRepository,
    InMemoryPetriSegmentationRegionRepository,
)


def _build_region(region_repository) -> PetriSegmentationRegion:
    region = PetriSegmentationRegion(
        segmentation_run_id=uuid4(),
        dataset_release_id=uuid4(),
        dataset_item_id=uuid4(),
        dataset_split_item_id=uuid4(),
        split=DatasetSplit.TRAIN,
        petri_image_path="/data/petri/sample_001.jpg",
        region_index=0,
        area_px=120.0,
        centroid_x=10.0,
        centroid_y=12.0,
        bbox_x=1,
        bbox_y=2,
        bbox_width=20,
        bbox_height=22,
    )
    region_repository.add_many([region])
    return region


def _build_use_case(*, review_repository=None):
    region_repo = InMemoryPetriSegmentationRegionRepository()
    review_repo = review_repository or InMemoryPetriRegionReviewRepository()
    uow = FakeUnitOfWork(analysis_run_repository=None, prediction_repository=None, petri_region_review_repository=review_repo)
    use_case = SubmitPetriRegionReviewUseCase(region_repo, uow)
    return use_case, region_repo, review_repo


def test_creates_review_with_candidate_valid_decision():
    use_case, region_repo, review_repo = _build_use_case()
    region = _build_region(region_repo)

    result = use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.CANDIDATE_VALID,
        )
    )

    assert result.decision == PetriRegionReviewDecision.CANDIDATE_VALID
    assert result.is_final is True
    assert review_repo.get_final_by_region_id(region.id).id == result.id


def test_creates_review_with_candidate_false_positive_decision():
    use_case, region_repo, _ = _build_use_case()
    region = _build_region(region_repo)

    result = use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.CANDIDATE_FALSE_POSITIVE,
        )
    )

    assert result.decision == PetriRegionReviewDecision.CANDIDATE_FALSE_POSITIVE


def test_creates_review_with_candidate_uncertain_decision():
    use_case, region_repo, _ = _build_use_case()
    region = _build_region(region_repo)

    result = use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.CANDIDATE_UNCERTAIN,
        )
    )

    assert result.decision == PetriRegionReviewDecision.CANDIDATE_UNCERTAIN


def test_creates_review_with_needs_resegmentation_decision():
    use_case, region_repo, _ = _build_use_case()
    region = _build_region(region_repo)

    result = use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.NEEDS_RESEGMENTATION,
        )
    )

    assert result.decision == PetriRegionReviewDecision.NEEDS_RESEGMENTATION


def test_rejects_review_when_region_does_not_exist():
    use_case, *_ = _build_use_case()

    with pytest.raises(PetriSegmentationRegionNotFoundError):
        use_case.execute(
            SubmitPetriRegionReviewRequest(
                petri_segmentation_region_id=uuid4(),
                decision=PetriRegionReviewDecision.CANDIDATE_VALID,
            )
        )


def test_rejects_confidence_score_below_zero():
    use_case, region_repo, _ = _build_use_case()
    region = _build_region(region_repo)

    with pytest.raises(ValueError):
        use_case.execute(
            SubmitPetriRegionReviewRequest(
                petri_segmentation_region_id=region.id,
                decision=PetriRegionReviewDecision.CANDIDATE_VALID,
                confidence_score=-0.1,
            )
        )


def test_rejects_confidence_score_above_one():
    use_case, region_repo, _ = _build_use_case()
    region = _build_region(region_repo)

    with pytest.raises(ValueError):
        use_case.execute(
            SubmitPetriRegionReviewRequest(
                petri_segmentation_region_id=region.id,
                decision=PetriRegionReviewDecision.CANDIDATE_VALID,
                confidence_score=1.1,
            )
        )


def test_rejects_corrected_bbox_with_non_positive_width():
    use_case, region_repo, _ = _build_use_case()
    region = _build_region(region_repo)

    with pytest.raises(ValueError):
        use_case.execute(
            SubmitPetriRegionReviewRequest(
                petri_segmentation_region_id=region.id,
                decision=PetriRegionReviewDecision.CANDIDATE_VALID,
                corrected_bbox_width=0,
                corrected_bbox_height=10,
            )
        )


def test_rejects_corrected_bbox_with_non_positive_height():
    use_case, region_repo, _ = _build_use_case()
    region = _build_region(region_repo)

    with pytest.raises(ValueError):
        use_case.execute(
            SubmitPetriRegionReviewRequest(
                petri_segmentation_region_id=region.id,
                decision=PetriRegionReviewDecision.CANDIDATE_VALID,
                corrected_bbox_width=10,
                corrected_bbox_height=-1,
            )
        )


def test_new_final_review_demotes_previous_final_review():
    use_case, region_repo, review_repo = _build_use_case()
    region = _build_region(region_repo)

    first = use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.CANDIDATE_VALID,
        )
    )
    second = use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.CANDIDATE_FALSE_POSITIVE,
        )
    )

    reviews = review_repo.list_by_region_id(region.id)
    assert len(reviews) == 2
    assert review_repo.get_by_id(first.id).is_final is False
    assert review_repo.get_by_id(second.id).is_final is True


def test_non_final_review_does_not_demote_previous_final_review():
    use_case, region_repo, review_repo = _build_use_case()
    region = _build_region(region_repo)

    first = use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.CANDIDATE_VALID,
        )
    )
    use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.CANDIDATE_UNCERTAIN,
            is_final=False,
        )
    )

    assert review_repo.get_by_id(first.id).is_final is True
    assert review_repo.get_final_by_region_id(region.id).id == first.id


def test_does_not_modify_original_region():
    use_case, region_repo, _ = _build_use_case()
    region = _build_region(region_repo)

    use_case.execute(
        SubmitPetriRegionReviewRequest(
            petri_segmentation_region_id=region.id,
            decision=PetriRegionReviewDecision.CANDIDATE_VALID,
            corrected_bbox_x=5,
            corrected_bbox_y=6,
            corrected_bbox_width=30,
            corrected_bbox_height=32,
        )
    )

    stored_region = region_repo.get_by_id(region.id)
    assert stored_region.bbox_x == 1
    assert stored_region.bbox_y == 2
    assert stored_region.bbox_width == 20
    assert stored_region.bbox_height == 22


def test_rollback_preserves_previous_final_when_new_final_insert_fails():
    base_review_repo = InMemoryPetriRegionReviewRepository()
    failing_review_repo = FailingAddPetriRegionReviewRepository(base_review_repo)
    use_case, region_repo, _ = _build_use_case(review_repository=failing_review_repo)
    region = _build_region(region_repo)

    first_review = base_review_repo.add(
        PetriRegionReview(
            petri_segmentation_region_id=region.id,
            petri_segmentation_run_id=region.segmentation_run_id,
            dataset_release_id=region.dataset_release_id,
            dataset_item_id=region.dataset_item_id,
            dataset_split_item_id=region.dataset_split_item_id,
            decision=PetriRegionReviewDecision.CANDIDATE_VALID,
            is_final=True,
        )
    )

    with pytest.raises(RuntimeError, match="simulated petri region review insert failure"):
        use_case.execute(
            SubmitPetriRegionReviewRequest(
                petri_segmentation_region_id=region.id,
                decision=PetriRegionReviewDecision.CANDIDATE_FALSE_POSITIVE,
            )
        )

    assert base_review_repo.get_by_id(first_review.id).is_final is True
    assert base_review_repo.get_final_by_region_id(region.id).id == first_review.id
    assert len(base_review_repo.list_by_region_id(region.id)) == 1
