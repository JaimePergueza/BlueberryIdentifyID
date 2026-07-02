import pytest

from blueberry_microid.application.dto.model_version_dto import CreateModelVersionRequest
from blueberry_microid.application.exceptions import InvalidModelTypeError
from blueberry_microid.application.use_cases.model_version.create_model_version import CreateModelVersionUseCase
from tests.unit.application.fakes import InMemoryModelVersionRepository


def test_create_model_version_of_type_mock():
    use_case = CreateModelVersionUseCase(InMemoryModelVersionRepository())

    dto = use_case.execute(CreateModelVersionRequest(name="stub-engine", version="0.1.0", model_type="mock"))

    assert dto.model_type == "mock"
    assert dto.is_active is True


def test_create_model_version_rejects_invalid_model_type():
    use_case = CreateModelVersionUseCase(InMemoryModelVersionRepository())

    with pytest.raises(InvalidModelTypeError):
        use_case.execute(CreateModelVersionRequest(name="bad-engine", version="0.1.0", model_type="tensorflow"))
