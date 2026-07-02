from sqlalchemy.exc import IntegrityError

from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
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
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository


def _create_analysis_run(db_session):
    sample = SqlAlchemySampleRepository(db_session).add(Sample(sample_code="S-950"))
    petri_image = SqlAlchemyPetriImageRepository(db_session).add(
        PetriImage(sample_id=sample.id, file_path="/p", file_name="p.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    micro_image = SqlAlchemyMicroImageRepository(db_session).add(
        MicroImage(sample_id=sample.id, file_path="/m", file_name="m.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    model_version = SqlAlchemyModelVersionRepository(db_session).add(
        ModelVersion(name="stub", version="0.1.0", model_type=ModelType.MOCK)
    )
    analysis_run = AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id)
    return SqlAlchemyAnalysisRunRepository(db_session).add(analysis_run)


def test_a_non_final_review_can_coexist_with_a_final_one(db_session):
    analysis_run = _create_analysis_run(db_session)

    db_session.add(
        HumanReviewModel(
            analysis_run_id=analysis_run.id, reviewer_name="Dra. Lopez", review_decision="confirmed", is_final=True
        )
    )
    db_session.commit()

    db_session.add(
        HumanReviewModel(
            analysis_run_id=analysis_run.id, reviewer_name="Dr. Perez", review_decision="confirmed", is_final=False
        )
    )
    db_session.commit()

    assert db_session.query(HumanReviewModel).filter_by(analysis_run_id=analysis_run.id).count() == 2


def test_only_one_final_review_allowed_per_analysis_run(db_session):
    analysis_run = _create_analysis_run(db_session)

    db_session.add(
        HumanReviewModel(
            analysis_run_id=analysis_run.id, reviewer_name="Dra. Lopez", review_decision="confirmed", is_final=True
        )
    )
    db_session.commit()

    db_session.add(
        HumanReviewModel(
            analysis_run_id=analysis_run.id, reviewer_name="Dr. Perez", review_decision="confirmed", is_final=True
        )
    )
    try:
        db_session.commit()
        assert False, "a second final review for the same analysis_run must be rejected"
    except IntegrityError:
        db_session.rollback()
