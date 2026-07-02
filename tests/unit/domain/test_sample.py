import pytest

from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.exceptions.errors import EmptySampleCodeError, UnsupportedProductError


def test_sample_created_with_valid_code_and_default_product():
    sample = Sample(sample_code="S-001")

    assert sample.sample_code == "S-001"
    assert sample.product == "blueberry"


@pytest.mark.parametrize("blank_code", ["", "   ", "\t"])
def test_sample_rejects_empty_sample_code(blank_code):
    with pytest.raises(EmptySampleCodeError):
        Sample(sample_code=blank_code)


def test_sample_rejects_non_blueberry_product():
    with pytest.raises(UnsupportedProductError):
        Sample(sample_code="S-002", product="strawberry")
