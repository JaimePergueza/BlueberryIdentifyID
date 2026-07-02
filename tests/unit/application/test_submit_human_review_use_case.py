from uuid import uuid4

import pytest

from blueberry_microid.application.dto.human_review_dto import SubmitHumanReviewRequest
from blueberry_microid.application.exceptions import (
    AnalysisRunNotFoundError,
    AnalysisRunNotReviewableError,
    PredictionNotFoundError,
)
from blueberry_microid.application.use_cases.review.submit_human_review import SubmitHumanReviewUseCase
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.exceptions.errors import MissingCorrectedLabelError
from tests.unit.application.fakes import (
    FailingAddHumanReviewRepository,
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryHumanReviewRepository,
    InMemoryMicroImageRepository,
    InMemoryModelVersionRepository,
    InMemoryPetriImageRepository,
    InMemoryPredictionRepository,
)


def _build_run(
    analysis_run_repository,
    petri_repository,
    micro_repository,
    model_version_repository,
    *,
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
):
    sample_id = uuid4()
    petri_image = petri_repository.add(
        PetriImage(sample_id=sample_id, file_path="/p", file_name="p.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    micro_image = micro_repository.add(
        MicroImage(sample_id=sample_id, file_path="/m", file_name="m.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    model_version = model_version_repository.add(ModelVersion(name="stub", version=str(uuid4()), model_type=ModelType.MOCK))
    run = AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id)
    if status != AnalysisStatus.PENDING:
        run.mark_processing()
    if status == AnalysisStatus.COMPLETED:
        run.mark_completed()
    elif status == AnalysisStatus.NEEDS_REVIEW:
        run.mark_needs_review()
    elif status == AnalysisStatus.FAILED:
        run.mark_failed("simulated failure")
    return analysis_run_repository.add(run)


def _build_use_case(*, human_review_repository=None):
    run_repo = InMemoryAnalysisRunRepository()
    petri_repo = InMemoryPetriImageRepository()
    micro_repo = InMemoryMicroImageRepository()
    model_version_repo = InMemoryModelVersionRepository()
    pred_repo = InMemoryPredictionRepository()
    review_repo = human_review_repository or InMemoryHumanReviewRepository()
    uow = FakeUnitOfWork(run_repo, pred_repo, review_repo)
    use_case = SubmitHumanReviewUseCase(run_repo, pred_repo, uow)
    return use_case, run_repo, petri_repo, micro_repo, model_version_repo, pred_repo, review_repo


def _add_prediction(prediction_repository, analysis_run_id):
    return prediction_repository.add(
        Prediction(
            analysis_run_id=analysis_run_id,
            predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
            confidence_score=0.6,
            technical_observation="original mock prediction",
            requires_human_review=True,
        )
    )


def test_creates_valid_confirmed_review():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, review_repo = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo)
    _add_prediction(pred_repo, run.id)

    result = use_case.execute(
        SubmitHumanReviewRequest(
            analysis_run_id=run.id,
            reviewer_name="Dra. Lopez",
            review_decision=ReviewDecision.CONFIRMED,
        )
    )

    assert result.review_decision == ReviewDecision.CONFIRMED
    assert result.corrected_label is None
    assert result.is_final is True
    assert review_repo.get_final_by_analysis_run_id(run.id).id == result.id


def test_creates_valid_corrected_review_with_corrected_label():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo)
    _add_prediction(pred_repo, run.id)

    result = use_case.execute(
        SubmitHumanReviewRequest(
            analysis_run_id=run.id,
            reviewer_name="Dra. Lopez",
            review_decision=ReviewDecision.CORRECTED,
            corrected_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH,
            comments="Corrected broad preliminary category.",
        )
    )

    assert result.review_decision == ReviewDecision.CORRECTED
    assert result.corrected_label == PredictedLabel.PROBABLE_FUNGAL_GROWTH


def test_rejects_corrected_review_without_corrected_label():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo)
    _add_prediction(pred_repo, run.id)

    with pytest.raises(MissingCorrectedLabelError):
        use_case.execute(
            SubmitHumanReviewRequest(
                analysis_run_id=run.id,
                reviewer_name="Dra. Lopez",
                review_decision=ReviewDecision.CORRECTED,
            )
        )


def test_creates_marked_inconclusive_review():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo, status=AnalysisStatus.NEEDS_REVIEW)
    _add_prediction(pred_repo, run.id)

    result = use_case.execute(
        SubmitHumanReviewRequest(
            analysis_run_id=run.id,
            reviewer_name="Dra. Lopez",
            review_decision=ReviewDecision.MARKED_INCONCLUSIVE,
            corrected_label=PredictedLabel.INCONCLUSIVE,
        )
    )

    assert result.review_decision == ReviewDecision.MARKED_INCONCLUSIVE
    assert result.corrected_label == PredictedLabel.INCONCLUSIVE


def test_creates_rejected_invalid_sample_review():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo, status=AnalysisStatus.FAILED)
    _add_prediction(pred_repo, run.id)

    result = use_case.execute(
        SubmitHumanReviewRequest(
            analysis_run_id=run.id,
            reviewer_name="Dra. Lopez",
            review_decision=ReviewDecision.REJECTED_INVALID_SAMPLE,
            comments="Microscopy preparation is not usable.",
        )
    )

    assert result.review_decision == ReviewDecision.REJECTED_INVALID_SAMPLE
    assert result.comments == "Microscopy preparation is not usable."


def test_rejects_review_when_analysis_run_does_not_exist():
    use_case, *_ = _build_use_case()

    with pytest.raises(AnalysisRunNotFoundError):
        use_case.execute(
            SubmitHumanReviewRequest(
                analysis_run_id=uuid4(),
                reviewer_name="Dra. Lopez",
                review_decision=ReviewDecision.CONFIRMED,
            )
        )


def test_rejects_review_when_prediction_does_not_exist():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, *_ = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo)

    with pytest.raises(PredictionNotFoundError):
        use_case.execute(
            SubmitHumanReviewRequest(
                analysis_run_id=run.id,
                reviewer_name="Dra. Lopez",
                review_decision=ReviewDecision.CONFIRMED,
            )
        )


def test_rejects_review_when_analysis_run_is_pending():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo, status=AnalysisStatus.PENDING)
    _add_prediction(pred_repo, run.id)

    with pytest.raises(AnalysisRunNotReviewableError):
        use_case.execute(
            SubmitHumanReviewRequest(
                analysis_run_id=run.id,
                reviewer_name="Dra. Lopez",
                review_decision=ReviewDecision.CONFIRMED,
            )
        )


def test_rejects_review_when_analysis_run_is_processing():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo, status=AnalysisStatus.PROCESSING)
    _add_prediction(pred_repo, run.id)

    with pytest.raises(AnalysisRunNotReviewableError):
        use_case.execute(
            SubmitHumanReviewRequest(
                analysis_run_id=run.id,
                reviewer_name="Dra. Lopez",
                review_decision=ReviewDecision.CONFIRMED,
            )
        )


def test_new_final_review_demotes_previous_final_review():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, review_repo = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo)
    _add_prediction(pred_repo, run.id)
    first = use_case.execute(
        SubmitHumanReviewRequest(run.id, "Dra. Lopez", ReviewDecision.CONFIRMED)
    )

    second = use_case.execute(
        SubmitHumanReviewRequest(
            run.id,
            "Dr. Perez",
            ReviewDecision.CORRECTED,
            corrected_label=PredictedLabel.NO_EVIDENT_GROWTH,
        )
    )

    reviews = review_repo.list_by_analysis_run_id(run.id)
    assert len(reviews) == 2
    assert review_repo.get_by_id(first.id).is_final is False
    assert review_repo.get_by_id(second.id).is_final is True


def test_rollback_preserves_previous_final_when_new_final_insert_fails():
    base_review_repo = InMemoryHumanReviewRepository()
    failing_review_repo = FailingAddHumanReviewRepository(base_review_repo)
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case(
        human_review_repository=failing_review_repo
    )
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo)
    _add_prediction(pred_repo, run.id)

    first_review = base_review_repo.add(
        HumanReview(
            analysis_run_id=run.id,
            reviewer_name="Dra. Lopez",
            review_decision=ReviewDecision.CONFIRMED,
            is_final=True,
        )
    )

    with pytest.raises(RuntimeError, match="simulated human review insert failure"):
        use_case.execute(
            SubmitHumanReviewRequest(
                run.id,
                "Dr. Perez",
                ReviewDecision.CORRECTED,
                corrected_label=PredictedLabel.NO_EVIDENT_GROWTH,
            )
        )

    assert base_review_repo.get_by_id(first_review.id).is_final is True
    assert base_review_repo.get_final_by_analysis_run_id(run.id).id == first_review.id
    assert len(base_review_repo.list_by_analysis_run_id(run.id)) == 1


def test_review_does_not_modify_original_prediction():
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case()
    run = _build_run(run_repo, petri_repo, micro_repo, mv_repo)
    prediction = _add_prediction(pred_repo, run.id)

    use_case.execute(
        SubmitHumanReviewRequest(
            run.id,
            "Dra. Lopez",
            ReviewDecision.CORRECTED,
            corrected_label=PredictedLabel.NO_EVIDENT_GROWTH,
        )
    )

    stored_prediction = pred_repo.get_by_analysis_run_id(run.id)
    assert stored_prediction.id == prediction.id
    assert stored_prediction.predicted_label == PredictedLabel.SUSPICIOUS_GROWTH
    assert stored_prediction.technical_observation == "original mock prediction"
