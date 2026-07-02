import pytest

from blueberry_microid.application.dto.sample_dto import CreateSampleRequest
from blueberry_microid.application.exceptions import DuplicateSampleCodeError
from blueberry_microid.application.use_cases.sample.create_sample import CreateSampleUseCase
from tests.unit.application.fakes import InMemorySampleRepository


def test_create_sample_with_valid_data():
    use_case = CreateSampleUseCase(InMemorySampleRepository())

    dto = use_case.execute(CreateSampleRequest(sample_code="S-100", origin="Field A"))

    assert dto.sample_code == "S-100"
    assert dto.product == "blueberry"
    assert dto.origin == "Field A"


def test_create_sample_rejects_duplicate_sample_code():
    sample_repository = InMemorySampleRepository()
    use_case = CreateSampleUseCase(sample_repository)
    use_case.execute(CreateSampleRequest(sample_code="S-101"))

    with pytest.raises(DuplicateSampleCodeError):
        use_case.execute(CreateSampleRequest(sample_code="S-101"))
