"""Verifies real cross-repository atomicity for ProcessAnalysisRunUseCase's
success path, using the actual `SqlAlchemyUnitOfWork` against SQLite (the
in-memory fakes used elsewhere cannot prove this — see
tests/unit/application/test_process_analysis_run_use_case.py).
"""

import pytest

from blueberry_microid.application.exceptions import AnalysisProcessingError, DuplicatePredictionError
from blueberry_microid.application.ports.inference_engine import InferenceOutput
from blueberry_microid.application.use_cases.inference.process_analysis_run import ProcessAnalysisRunUseCase
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_analysis_run_repository import (
    SqlAlchemyAnalysisRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_micro_image_repository import (
    SqlAlchemyMicroImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_model_version_repository import (
    SqlAlchemyModelVersionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_image_repository import (
    SqlAlchemyPetriImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_prediction_repository import (
    SqlAlchemyPredictionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from tests.unit.application.fakes import FailingInferenceEngine, FakeInferenceEngine


def _build_pending_run(session):
    sample = SqlAlchemySampleRepository(session).add(Sample(sample_code="S-TX-1"))
    petri_image = SqlAlchemyPetriImageRepository(session).add(
        PetriImage(sample_id=sample.id, file_path="/p", file_name="p.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    micro_image = SqlAlchemyMicroImageRepository(session).add(
        MicroImage(sample_id=sample.id, file_path="/m", file_name="m.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    model_version = SqlAlchemyModelVersionRepository(session).add(
        ModelVersion(name="stub-tx", version="0.1.0", model_type=ModelType.MOCK)
    )
    run_repository = SqlAlchemyAnalysisRunRepository(session)
    run = run_repository.add(
        AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id)
    )
    return run, run_repository


def test_unit_of_work_commits_prediction_and_final_status_together(sqlite_engine, db_session):
    run, run_repository = _build_pending_run(db_session)
    run.mark_processing()
    run_repository.update(run)
    run.mark_completed()
    prediction = Prediction(analysis_run_id=run.id, predicted_label=PredictedLabel.NO_EVIDENT_GROWTH, confidence_score=0.6)

    session_factory = create_session_factory(sqlite_engine)
    uow = SqlAlchemyUnitOfWork(session_factory)
    with uow:
        uow.prediction_repository.add(prediction)
        uow.analysis_run_repository.update(run)
        uow.commit()

    persisted_run = run_repository.get_by_id(run.id)
    assert persisted_run.status == AnalysisStatus.COMPLETED
    assert SqlAlchemyAnalysisRunRepository(db_session).get_by_id(run.id).status == AnalysisStatus.COMPLETED


def test_unit_of_work_rolls_back_both_writes_when_prediction_insert_fails(sqlite_engine, db_session):
    """A duplicate Prediction (analysis_run_id already has one) must not
    leave the AnalysisRun's status change persisted either — proving the
    two writes are genuinely atomic, not just sequential.
    """
    run, run_repository = _build_pending_run(db_session)
    run.mark_processing()
    run_repository.update(run)
    run.mark_completed()

    session_factory = create_session_factory(sqlite_engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    # First prediction succeeds and commits normally.
    first_prediction = Prediction(analysis_run_id=run.id, predicted_label=PredictedLabel.NO_EVIDENT_GROWTH, confidence_score=0.6)
    with uow:
        uow.prediction_repository.add(first_prediction)
        uow.analysis_run_repository.update(run)
        uow.commit()

    # Simulate reprocessing attempting a second Prediction for the same
    # AnalysisRun bundled with a further status write — the duplicate
    # constraint must roll back *both* within this transaction.
    run.status = AnalysisStatus.PROCESSING  # pretend we are mid-reprocessing, in-memory only
    second_prediction = Prediction(analysis_run_id=run.id, predicted_label=PredictedLabel.SUSPICIOUS_GROWTH, confidence_score=0.6)

    from blueberry_microid.application.exceptions import DuplicatePredictionError

    try:
        with uow:
            uow.analysis_run_repository.update(run)  # would move status to `processing` if committed
            uow.prediction_repository.add(second_prediction)  # fails: duplicate
            uow.commit()
    except DuplicatePredictionError:
        pass

    # The in-transaction status change to `processing` must NOT have
    # persisted, because the whole block rolled back.
    reloaded = SqlAlchemyAnalysisRunRepository(db_session).get_by_id(run.id)
    assert reloaded.status == AnalysisStatus.COMPLETED


def test_full_use_case_leaves_analysis_run_failed_not_stuck_processing(sqlite_engine, db_session):
    """End-to-end proof (Task 5/2) against the real stack — not the in-memory
    fakes: when the inference engine raises, `ProcessAnalysisRunUseCase`
    must leave the AnalysisRun `failed` with an error_message, never stuck
    in `processing`, using the real `SqlAlchemyUnitOfWork` and repositories.
    """
    run, run_repository = _build_pending_run(db_session)
    session_factory = create_session_factory(sqlite_engine)

    use_case = ProcessAnalysisRunUseCase(
        analysis_run_repository=run_repository,
        petri_image_repository=SqlAlchemyPetriImageRepository(db_session),
        micro_image_repository=SqlAlchemyMicroImageRepository(db_session),
        model_version_repository=SqlAlchemyModelVersionRepository(db_session),
        inference_engine=FailingInferenceEngine(),
        unit_of_work=SqlAlchemyUnitOfWork(session_factory),
    )

    with pytest.raises(AnalysisProcessingError):
        use_case.execute(run.id)

    persisted = SqlAlchemyAnalysisRunRepository(db_session).get_by_id(run.id)
    assert persisted.status == AnalysisStatus.FAILED
    assert persisted.error_message == "Analysis processing failed"


def test_duplicate_prediction_during_finalization_marks_analysis_run_failed(sqlite_engine, db_session):
    """A Prediction that already exists for a still-`pending` AnalysisRun is
    a data anomaly that should be structurally impossible once claiming is
    exclusive (see `claim_for_processing`). If it ever occurs, the
    finalizing transaction (Prediction insert + status update) must roll
    back as a whole via real SQLite rollback. After that rollback, the use
    case must persist a controlled `failed` state instead of leaving the
    AnalysisRun stuck in `processing`.
    """
    run, run_repository = _build_pending_run(db_session)
    SqlAlchemyPredictionRepository(db_session).add(
        Prediction(analysis_run_id=run.id, predicted_label=PredictedLabel.NO_EVIDENT_GROWTH, confidence_score=0.6)
    )

    session_factory = create_session_factory(sqlite_engine)
    use_case = ProcessAnalysisRunUseCase(
        analysis_run_repository=run_repository,
        petri_image_repository=SqlAlchemyPetriImageRepository(db_session),
        micro_image_repository=SqlAlchemyMicroImageRepository(db_session),
        model_version_repository=SqlAlchemyModelVersionRepository(db_session),
        inference_engine=FakeInferenceEngine(
            InferenceOutput(
                predicted_label=PredictedLabel.NO_EVIDENT_GROWTH,
                confidence_score=0.6,
                class_probabilities={"no_evident_growth": 0.6},
                technical_observation="mock",
                requires_human_review=False,
            )
        ),
        unit_of_work=SqlAlchemyUnitOfWork(session_factory),
    )

    with pytest.raises(DuplicatePredictionError):
        use_case.execute(run.id)

    # The claim (pending -> processing) committed on its own before
    # finalization began; after the duplicate insert fails and rolls back,
    # the recovery write must advance the run to `failed`.
    persisted = SqlAlchemyAnalysisRunRepository(db_session).get_by_id(run.id)
    assert persisted.status == AnalysisStatus.FAILED
    assert persisted.error_message == "Prediction already exists for this analysis run"
