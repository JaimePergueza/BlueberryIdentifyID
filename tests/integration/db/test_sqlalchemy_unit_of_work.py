import uuid

import pytest
from sqlalchemy.orm import Session

from blueberry_microid.infrastructure.db.models import SampleModel, PetriImageModel, MicroImageModel
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def test_unit_of_work_commits_on_explicit_commit(sqlite_engine):
    session_factory = create_session_factory(sqlite_engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    with uow:
        uow.session.add(SampleModel(id=uuid.uuid4(), sample_code="S-900", product="blueberry"))
        uow.commit()

    with Session(sqlite_engine) as session:
        assert session.query(SampleModel).count() == 1


def test_unit_of_work_rolls_back_without_explicit_commit(sqlite_engine):
    session_factory = create_session_factory(sqlite_engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    with uow:
        uow.session.add(SampleModel(id=uuid.uuid4(), sample_code="S-901", product="blueberry"))
        # no uow.commit() here

    with Session(sqlite_engine) as session:
        assert session.query(SampleModel).count() == 0


def test_unit_of_work_rolls_back_on_exception(sqlite_engine):
    session_factory = create_session_factory(sqlite_engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(RuntimeError, match="simulated failure"):
        with uow:
            uow.session.add(SampleModel(id=uuid.uuid4(), sample_code="S-902", product="blueberry"))
            raise RuntimeError("simulated failure mid-transaction")

    with Session(sqlite_engine) as session:
        assert session.query(SampleModel).count() == 0


def test_paired_image_repositories_share_the_transaction(sqlite_engine):
    uow = SqlAlchemyUnitOfWork(create_session_factory(sqlite_engine))
    with pytest.raises(RuntimeError, match="analysis failed"):
        with uow:
            sample = uow.sample_repository.add(Sample(sample_code="ATOMIC-PAIR"))
            uow.petri_image_repository.add(PetriImage(
                sample_id=sample.id, file_path="/fake/petri.png", file_name="petri.png",
                mime_type="image/png", file_size_bytes=100,
            ))
            uow.micro_image_repository.add(MicroImage(
                sample_id=sample.id, file_path="/fake/micro.png", file_name="micro.png",
                mime_type="image/png", file_size_bytes=100,
            ))
            raise RuntimeError("analysis failed")

    with Session(sqlite_engine) as session:
        assert session.query(SampleModel).count() == 0
        assert session.query(PetriImageModel).count() == 0
        assert session.query(MicroImageModel).count() == 0
