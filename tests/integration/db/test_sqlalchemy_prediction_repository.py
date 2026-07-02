import pytest

from blueberry_microid.application.exceptions import DuplicatePredictionError
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
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


def _build_pending_run(db_session):
    sample = SqlAlchemySampleRepository(db_session).add(Sample(sample_code="S-PRED-1"))
    petri_image = SqlAlchemyPetriImageRepository(db_session).add(
        PetriImage(sample_id=sample.id, file_path="/p", file_name="p.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    micro_image = SqlAlchemyMicroImageRepository(db_session).add(
        MicroImage(sample_id=sample.id, file_path="/m", file_name="m.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    model_version = SqlAlchemyModelVersionRepository(db_session).add(
        ModelVersion(name="stub-pred", version="0.1.0", model_type=ModelType.MOCK)
    )
    return SqlAlchemyAnalysisRunRepository(db_session).add(
        AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id)
    )


def test_add_and_get_by_id(db_session):
    run = _build_pending_run(db_session)
    repository = SqlAlchemyPredictionRepository(db_session)
    prediction = Prediction(
        analysis_run_id=run.id,
        predicted_label=PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
        confidence_score=0.63,
        class_probabilities={"probable_bacterial_growth": 0.63, "no_evident_growth": 0.37},
        technical_observation="mock",
    )

    created = repository.add(prediction)
    fetched = repository.get_by_id(created.id)

    assert fetched is not None
    assert fetched.predicted_label == PredictedLabel.PROBABLE_BACTERIAL_GROWTH
    assert fetched.class_probabilities == {"probable_bacterial_growth": 0.63, "no_evident_growth": 0.37}


def test_get_by_analysis_run_id(db_session):
    run = _build_pending_run(db_session)
    repository = SqlAlchemyPredictionRepository(db_session)
    repository.add(Prediction(analysis_run_id=run.id, predicted_label=PredictedLabel.NO_EVIDENT_GROWTH, confidence_score=0.6))

    fetched = repository.get_by_analysis_run_id(run.id)

    assert fetched is not None
    assert fetched.analysis_run_id == run.id


def test_rejects_a_second_prediction_for_the_same_analysis_run(db_session):
    run = _build_pending_run(db_session)
    repository = SqlAlchemyPredictionRepository(db_session)
    repository.add(Prediction(analysis_run_id=run.id, predicted_label=PredictedLabel.NO_EVIDENT_GROWTH, confidence_score=0.6))

    with pytest.raises(DuplicatePredictionError):
        repository.add(Prediction(analysis_run_id=run.id, predicted_label=PredictedLabel.SUSPICIOUS_GROWTH, confidence_score=0.58))
