import logging
from uuid import uuid4

import pytest

from blueberry_microid.application.exceptions import (
    AnalysisProcessingError,
    AnalysisRunFinalizationError,
    AnalysisRunNotFoundError,
    DuplicatePredictionError,
)
from blueberry_microid.application.ports.inference_engine import InferenceOutput
from blueberry_microid.application.use_cases.inference.process_analysis_run import ProcessAnalysisRunUseCase
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.exceptions.errors import InvalidAnalysisRunTransitionError
from tests.unit.application.fakes import (
    FailingAddPredictionRepository,
    FailingInferenceEngine,
    FakeInferenceEngine,
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryMicroImageRepository,
    InMemoryModelVersionRepository,
    InMemoryPetriImageRepository,
    InMemoryPredictionRepository,
    UpdateFailingNTimesAnalysisRunRepository,
)


def _build_pending_run(analysis_run_repository, petri_repository, micro_repository, model_version_repository):
    sample_id = uuid4()
    petri_image = petri_repository.add(
        PetriImage(sample_id=sample_id, file_path="/p", file_name="p.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    micro_image = micro_repository.add(
        MicroImage(sample_id=sample_id, file_path="/m", file_name="m.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    model_version = model_version_repository.add(ModelVersion(name="stub", version="0.1.0", model_type=ModelType.MOCK))
    return analysis_run_repository.add(
        AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id)
    )


def _build_use_case(inference_engine):
    analysis_run_repository = InMemoryAnalysisRunRepository()
    petri_repository = InMemoryPetriImageRepository()
    micro_repository = InMemoryMicroImageRepository()
    model_version_repository = InMemoryModelVersionRepository()
    prediction_repository = InMemoryPredictionRepository()
    unit_of_work = FakeUnitOfWork(analysis_run_repository, prediction_repository)

    use_case = ProcessAnalysisRunUseCase(
        analysis_run_repository=analysis_run_repository,
        petri_image_repository=petri_repository,
        micro_image_repository=micro_repository,
        model_version_repository=model_version_repository,
        inference_engine=inference_engine,
        unit_of_work=unit_of_work,
    )
    return use_case, analysis_run_repository, petri_repository, micro_repository, model_version_repository, prediction_repository, unit_of_work


def _build_use_case_with_uow_repos(inference_engine, *, wrap_analysis_run_repository=None, wrap_prediction_repository=None):
    """Like `_build_use_case`, but lets a test wrap what the UoW exposes as
    `analysis_run_repository`/`prediction_repository` — used to simulate a
    failure specifically inside the transactional write, independent of the
    plain repository used for get_by_id()/claim_for_processing() (which
    must keep working normally so the claim itself still succeeds).
    """
    analysis_run_repository = InMemoryAnalysisRunRepository()
    petri_repository = InMemoryPetriImageRepository()
    micro_repository = InMemoryMicroImageRepository()
    model_version_repository = InMemoryModelVersionRepository()
    prediction_repository = InMemoryPredictionRepository()
    uow_analysis_run_repository = (
        wrap_analysis_run_repository(analysis_run_repository) if wrap_analysis_run_repository else analysis_run_repository
    )
    uow_prediction_repository = (
        wrap_prediction_repository(prediction_repository) if wrap_prediction_repository else prediction_repository
    )
    unit_of_work = FakeUnitOfWork(uow_analysis_run_repository, uow_prediction_repository)

    use_case = ProcessAnalysisRunUseCase(
        analysis_run_repository=analysis_run_repository,
        petri_image_repository=petri_repository,
        micro_image_repository=micro_repository,
        model_version_repository=model_version_repository,
        inference_engine=inference_engine,
        unit_of_work=unit_of_work,
    )
    return (
        use_case,
        analysis_run_repository,
        petri_repository,
        micro_repository,
        model_version_repository,
        prediction_repository,
        unit_of_work,
        uow_analysis_run_repository,
    )


def _successful_output(label: PredictedLabel = PredictedLabel.NO_EVIDENT_GROWTH) -> InferenceOutput:
    return InferenceOutput(
        predicted_label=label,
        confidence_score=0.6,
        class_probabilities={label.value: 0.6},
        technical_observation="mock",
        requires_human_review=False,
    )


def test_processes_a_pending_analysis_run():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, uow = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    result = use_case.execute(run.id)

    assert result.analysis_run.status == AnalysisStatus.COMPLETED
    assert uow.entered is True
    assert uow.committed is True


def test_creates_a_prediction():
    engine = FakeInferenceEngine(_successful_output(PredictedLabel.PROBABLE_FUNGAL_GROWTH))
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, uow = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    result = use_case.execute(run.id)

    assert result.prediction is not None
    assert result.prediction.predicted_label == PredictedLabel.PROBABLE_FUNGAL_GROWTH
    stored = pred_repo.get_by_analysis_run_id(run.id)
    assert stored is not None
    assert stored.id == result.prediction.id


def test_marks_completed_when_review_not_required():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, *_ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    result = use_case.execute(run.id)

    assert result.analysis_run.status == AnalysisStatus.COMPLETED
    assert result.analysis_run.completed_at is not None


def test_marks_needs_review_when_review_required():
    output = InferenceOutput(
        predicted_label=PredictedLabel.INCONCLUSIVE,
        confidence_score=0.55,
        class_probabilities={"inconclusive": 0.55},
        technical_observation="mock",
        requires_human_review=True,
    )
    engine = FakeInferenceEngine(output)
    use_case, run_repo, petri_repo, micro_repo, mv_repo, *_ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    result = use_case.execute(run.id)

    assert result.analysis_run.status == AnalysisStatus.NEEDS_REVIEW
    assert result.prediction.requires_human_review is True


def test_rejects_processing_a_nonexistent_analysis_run():
    engine = FakeInferenceEngine(_successful_output())
    use_case, *_ = _build_use_case(engine)

    with pytest.raises(AnalysisRunNotFoundError):
        use_case.execute(uuid4())


def test_does_not_reprocess_an_already_completed_analysis_run():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, *_ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    use_case.execute(run.id)

    with pytest.raises(InvalidAnalysisRunTransitionError):
        use_case.execute(run.id)


def test_marks_failed_when_inference_engine_raises():
    engine = FailingInferenceEngine()
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    with pytest.raises(AnalysisProcessingError) as exc_info:
        use_case.execute(run.id)

    stored = run_repo.get_by_id(run.id)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_message == "Analysis processing failed"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "simulated inference engine crash" in str(exc_info.value.__cause__)


def test_does_not_create_a_prediction_when_inference_engine_fails():
    engine = FailingInferenceEngine()
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    with pytest.raises(AnalysisProcessingError):
        use_case.execute(run.id)

    assert pred_repo.get_by_analysis_run_id(run.id) is None


def test_inference_engine_failure_logs_original_error(caplog):
    engine = FailingInferenceEngine()
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, _ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    with caplog.at_level(logging.ERROR, logger="blueberry_microid.business.process_analysis_run"):
        with pytest.raises(AnalysisProcessingError):
            use_case.execute(run.id)

    assert any(
        record.exc_info is not None and record.exc_info[0] is RuntimeError
        for record in caplog.records
    )


def test_uses_the_unit_of_work_for_the_transactional_writes():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, uow = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    assert uow.entered is False
    assert uow.committed is False

    use_case.execute(run.id)

    assert uow.entered is True
    assert uow.committed is True
    # The use case writes through uow.analysis_run_repository/
    # uow.prediction_repository (the same instances injected here), not
    # some other, disconnected repository.
    assert uow.analysis_run_repository is run_repo
    assert uow.prediction_repository is pred_repo


# --- Phase 4.5: idempotency, claim, and recovery -----------------------


def test_rejects_processing_when_already_processing():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, *_ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)
    run_repo.claim_for_processing(run.id)  # simulate another in-flight call

    with pytest.raises(InvalidAnalysisRunTransitionError, match="already being processed"):
        use_case.execute(run.id)


def test_rejects_processing_when_already_completed():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, *_ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)
    use_case.execute(run.id)

    with pytest.raises(InvalidAnalysisRunTransitionError, match="already been processed"):
        use_case.execute(run.id)


def test_rejects_processing_when_needs_review():
    output = InferenceOutput(
        predicted_label=PredictedLabel.INCONCLUSIVE,
        confidence_score=0.55,
        class_probabilities={"inconclusive": 0.55},
        technical_observation="mock",
        requires_human_review=True,
    )
    engine = FakeInferenceEngine(output)
    use_case, run_repo, petri_repo, micro_repo, mv_repo, *_ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)
    use_case.execute(run.id)

    with pytest.raises(InvalidAnalysisRunTransitionError, match="already been processed"):
        use_case.execute(run.id)


def test_rejects_processing_when_already_failed():
    engine = FailingInferenceEngine()
    use_case, run_repo, petri_repo, micro_repo, mv_repo, *_ = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)
    with pytest.raises(AnalysisProcessingError):
        use_case.execute(run.id)

    with pytest.raises(InvalidAnalysisRunTransitionError, match="create a new AnalysisRun"):
        use_case.execute(run.id)


def test_claim_for_processing_succeeds_only_once():
    """Directly exercises the repository-level claim contract that backs
    the idempotency/concurrency guarantee: a second claim on the same
    AnalysisRun must fail even though nothing else has changed its status.
    """
    run_repo = InMemoryAnalysisRunRepository()
    petri_repo = InMemoryPetriImageRepository()
    micro_repo = InMemoryMicroImageRepository()
    mv_repo = InMemoryModelVersionRepository()
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    first_claim = run_repo.claim_for_processing(run.id)
    second_claim = run_repo.claim_for_processing(run.id)

    assert first_claim is not None
    assert first_claim.status == AnalysisStatus.PROCESSING
    assert second_claim is None


def test_does_not_leave_processing_when_prediction_creation_fails():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, uow, _ = _build_use_case_with_uow_repos(
        engine, wrap_prediction_repository=lambda _repo: FailingAddPredictionRepository()
    )
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    with pytest.raises(AnalysisProcessingError) as exc_info:
        use_case.execute(run.id)

    stored = run_repo.get_by_id(run.id)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_message == "Analysis processing failed"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "simulated prediction insert failure" in str(exc_info.value.__cause__)
    assert pred_repo.get_by_analysis_run_id(run.id) is None


def test_attempts_mark_failed_when_final_status_write_fails():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, uow, flaky_run_repo = _build_use_case_with_uow_repos(
        engine, wrap_analysis_run_repository=lambda repo: UpdateFailingNTimesAnalysisRunRepository(repo, fail_call_count=1)
    )
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    with pytest.raises(AnalysisProcessingError):
        use_case.execute(run.id)

    # Call #1 (finalize as completed) failed; the recovery call #2
    # (mark_failed) went through the same flaky repository and succeeded.
    assert flaky_run_repo._update_calls == 2
    stored = run_repo.get_by_id(run.id)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_message == "Analysis processing failed"


def test_raises_finalization_error_when_marking_failed_also_fails():
    engine = FailingInferenceEngine()
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, uow, _ = _build_use_case_with_uow_repos(
        engine, wrap_analysis_run_repository=lambda repo: UpdateFailingNTimesAnalysisRunRepository(repo, fail_call_count=999)
    )
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    with pytest.raises(AnalysisRunFinalizationError) as exc_info:
        use_case.execute(run.id)

    # The original error must never be silently discarded.
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "simulated database failure" in str(exc_info.value.__cause__)


def test_does_not_create_a_second_prediction_after_successful_processing():
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, uow = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)

    use_case.execute(run.id)
    with pytest.raises(InvalidAnalysisRunTransitionError):
        use_case.execute(run.id)

    predictions_for_run = [p for p in pred_repo._by_id.values() if p.analysis_run_id == run.id]
    assert len(predictions_for_run) == 1


def test_duplicate_prediction_error_is_reraised_not_swallowed():
    """Structurally shouldn't happen once claiming is exclusive, but if a
    Prediction already exists for a `pending` run (e.g. a data anomaly), the
    use case must not leave the AnalysisRun in `processing`: it marks the
    run `failed`, then re-raises a controlled conflict for the API layer.
    """
    engine = FakeInferenceEngine(_successful_output())
    use_case, run_repo, petri_repo, micro_repo, mv_repo, pred_repo, uow = _build_use_case(engine)
    run = _build_pending_run(run_repo, petri_repo, micro_repo, mv_repo)
    pred_repo.add(Prediction(analysis_run_id=run.id, predicted_label=PredictedLabel.NO_EVIDENT_GROWTH, confidence_score=0.6))

    with pytest.raises(DuplicatePredictionError, match="Prediction already exists for this analysis run") as exc_info:
        use_case.execute(run.id)

    # Still exactly one Prediction for this run — the use case did not
    # attempt to add another one, nor did it swallow the error.
    predictions_for_run = [p for p in pred_repo._by_id.values() if p.analysis_run_id == run.id]
    assert len(predictions_for_run) == 1
    stored = run_repo.get_by_id(run.id)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_message == "Prediction already exists for this analysis run"
    assert isinstance(exc_info.value.__cause__, DuplicatePredictionError)
