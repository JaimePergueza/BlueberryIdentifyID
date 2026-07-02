import uuid

import pytest
from sqlalchemy.orm import Session

from blueberry_microid.infrastructure.db.models import SampleModel
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
