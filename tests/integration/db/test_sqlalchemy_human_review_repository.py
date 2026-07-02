import pytest

from blueberry_microid.application.exceptions import DuplicateFinalHumanReviewError
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_analysis_run_repository import (
    SqlAlchemyAnalysisRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_human_review_repository import (
    SqlAlchemyHumanReviewRepository,
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
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def _build_analysis_run(session):
    sample = SqlAlchemySampleRepository(session).add(Sample(sample_code="S-HR-1"))
    petri_image = SqlAlchemyPetriImageRepository(session).add(
        PetriImage(sample_id=sample.id, file_path="/p", file_name="p.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    micro_image = SqlAlchemyMicroImageRepository(session).add(
        MicroImage(sample_id=sample.id, file_path="/m", file_name="m.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    model_version = SqlAlchemyModelVersionRepository(session).add(
        ModelVersion(name="stub-review", version="0.1.0", model_type=ModelType.MOCK)
    )
    run = AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id)
    return SqlAlchemyAnalysisRunRepository(session).add(run)


def test_add_get_list_and_final_human_review(db_session):
    run = _build_analysis_run(db_session)
    repository = SqlAlchemyHumanReviewRepository(db_session)

    final_review = repository.add(
        HumanReview(
            analysis_run_id=run.id,
            reviewer_name="Dra. Lopez",
            review_decision=ReviewDecision.CONFIRMED,
            is_final=True,
        )
    )
    historical_review = repository.add(
        HumanReview(
            analysis_run_id=run.id,
            reviewer_name="Dr. Perez",
            review_decision=ReviewDecision.MARKED_INCONCLUSIVE,
            corrected_label=PredictedLabel.INCONCLUSIVE,
            is_final=False,
        )
    )

    assert repository.get_by_id(final_review.id).reviewer_name == "Dra. Lopez"
    assert repository.get_final_by_analysis_run_id(run.id).id == final_review.id
    assert [review.id for review in repository.list_by_analysis_run_id(run.id)] == [
        final_review.id,
        historical_review.id,
    ]


def test_unset_final_reviews_for_analysis_run(db_session):
    run = _build_analysis_run(db_session)
    repository = SqlAlchemyHumanReviewRepository(db_session)
    final_review = repository.add(
        HumanReview(analysis_run_id=run.id, reviewer_name="Dra. Lopez", review_decision=ReviewDecision.CONFIRMED)
    )

    count = repository.unset_final_reviews_for_analysis_run(run.id)

    assert count == 1
    assert repository.get_by_id(final_review.id).is_final is False
    assert repository.get_final_by_analysis_run_id(run.id) is None


def test_duplicate_final_review_raises_controlled_error(db_session):
    run = _build_analysis_run(db_session)
    repository = SqlAlchemyHumanReviewRepository(db_session)
    repository.add(
        HumanReview(analysis_run_id=run.id, reviewer_name="Dra. Lopez", review_decision=ReviewDecision.CONFIRMED)
    )

    with pytest.raises(DuplicateFinalHumanReviewError):
        repository.add(
            HumanReview(analysis_run_id=run.id, reviewer_name="Dr. Perez", review_decision=ReviewDecision.CONFIRMED)
        )


def test_unit_of_work_rolls_back_unset_when_new_final_review_insert_fails(sqlite_engine, db_session):
    run = _build_analysis_run(db_session)
    repository = SqlAlchemyHumanReviewRepository(db_session)
    first_review = repository.add(
        HumanReview(analysis_run_id=run.id, reviewer_name="Dra. Lopez", review_decision=ReviewDecision.CONFIRMED)
    )

    session_factory = create_session_factory(sqlite_engine)
    uow = SqlAlchemyUnitOfWork(session_factory)
    duplicate_primary_key_review = HumanReview(
        id=first_review.id,
        analysis_run_id=run.id,
        reviewer_name="Dr. Perez",
        review_decision=ReviewDecision.CORRECTED,
        corrected_label=PredictedLabel.NO_EVIDENT_GROWTH,
    )

    with pytest.raises(DuplicateFinalHumanReviewError):
        with uow:
            uow.human_review_repository.unset_final_reviews_for_analysis_run(run.id)
            uow.human_review_repository.add(duplicate_primary_key_review)
            uow.commit()

    db_session.expire_all()
    persisted = SqlAlchemyHumanReviewRepository(db_session).get_by_id(first_review.id)
    assert persisted.is_final is True
    assert SqlAlchemyHumanReviewRepository(db_session).get_final_by_analysis_run_id(run.id).id == first_review.id
