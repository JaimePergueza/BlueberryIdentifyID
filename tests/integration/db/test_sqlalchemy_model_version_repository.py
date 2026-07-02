import pytest

from blueberry_microid.application.exceptions import DuplicateModelVersionError
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_model_version_repository import (
    SqlAlchemyModelVersionRepository,
)


def test_add_and_get_by_id(db_session):
    repository = SqlAlchemyModelVersionRepository(db_session)
    model_version = ModelVersion(name="stub-engine", version="0.1.0", model_type=ModelType.MOCK)

    created = repository.add(model_version)
    fetched = repository.get_by_id(created.id)

    assert fetched is not None
    assert fetched.model_type == ModelType.MOCK
    assert fetched.is_active is True


def test_add_duplicate_name_and_version_raises(db_session):
    repository = SqlAlchemyModelVersionRepository(db_session)
    repository.add(ModelVersion(name="stub-engine", version="0.1.0", model_type=ModelType.MOCK))

    with pytest.raises(DuplicateModelVersionError):
        repository.add(ModelVersion(name="stub-engine", version="0.1.0", model_type=ModelType.MOCK))
