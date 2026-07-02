import pytest

from blueberry_microid.application.exceptions import DuplicateSampleCodeError
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository


def test_add_and_get_by_id(db_session):
    repository = SqlAlchemySampleRepository(db_session)
    sample = Sample(sample_code="S-500", origin="Field B")

    created = repository.add(sample)
    fetched = repository.get_by_id(created.id)

    assert fetched is not None
    assert fetched.sample_code == "S-500"
    assert fetched.origin == "Field B"
    assert fetched.product == "blueberry"


def test_get_by_sample_code(db_session):
    repository = SqlAlchemySampleRepository(db_session)
    repository.add(Sample(sample_code="S-501"))

    fetched = repository.get_by_sample_code("S-501")
    missing = repository.get_by_sample_code("does-not-exist")

    assert fetched is not None
    assert missing is None


def test_add_duplicate_sample_code_raises(db_session):
    repository = SqlAlchemySampleRepository(db_session)
    repository.add(Sample(sample_code="S-502"))

    with pytest.raises(DuplicateSampleCodeError):
        repository.add(Sample(sample_code="S-502"))
