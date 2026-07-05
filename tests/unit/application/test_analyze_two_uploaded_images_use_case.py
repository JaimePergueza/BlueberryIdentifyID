"""Unit tests for AnalyzeTwoUploadedImagesUseCase."""

import pytest

from blueberry_microid.application.dto.two_image_upload_dto import TwoImageUploadRequest, TwoImageUploadResult
from blueberry_microid.application.exceptions import ImageTooLargeError, InvalidImageError
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.image_validator import ImageValidationResult, ImageValidatorPort
from blueberry_microid.application.use_cases.analysis.analyze_two_uploaded_images import (
    AnalyzeTwoUploadedImagesUseCase,
)
from blueberry_microid.ml.inference_engine.preliminary_two_image_analysis_engine import (
    PreliminaryTwoImageAnalysisEngine,
)
from tests.unit.application.image_helpers import make_valid_jpeg_bytes


class _FakeValidator(ImageValidatorPort):
    def __init__(self, *, raise_error: bool = False) -> None:
        self._raise = raise_error

    def validate(self, *, file_name: str, mime_type: str, content: bytes) -> ImageValidationResult:
        if self._raise:
            raise InvalidImageError("fake invalid image")
        return ImageValidationResult(width=32, height=24)


class _FakeStorage(ImageStoragePort):
    def __init__(self, *, fail_on_category: ImageCategory | None = None) -> None:
        self._fail_on = fail_on_category
        self.saved: list[str] = []
        self.deleted: list[str] = []

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        if category == self._fail_on:
            raise OSError("fake storage failure")
        path = f"/fake/{category.value}/{original_file_name}"
        self.saved.append(path)
        return path

    def delete(self, path: str) -> None:
        self.deleted.append(path)


def _make_use_case(validator=None, storage=None, max_bytes=None):
    return AnalyzeTwoUploadedImagesUseCase(
        image_validator=validator or _FakeValidator(),
        upload_storage=storage or _FakeStorage(),
        engine=PreliminaryTwoImageAnalysisEngine(),
        max_upload_size_bytes=max_bytes,
    )


def _make_request(**kwargs):
    jpeg = make_valid_jpeg_bytes()
    defaults = dict(
        petri_file_name="petri.jpg",
        petri_mime_type="image/jpeg",
        petri_content=jpeg,
        micro_file_name="micro.jpg",
        micro_mime_type="image/jpeg",
        micro_content=jpeg,
    )
    defaults.update(kwargs)
    return TwoImageUploadRequest(**defaults)


def test_returns_result_with_valid_images():
    result = _make_use_case().execute(_make_request())
    assert isinstance(result, TwoImageUploadResult)
    assert result.upload_id
    assert result.predicted_label is not None
    assert 0.0 < result.confidence_score <= 1.0
    assert len(result.class_probabilities) == 5
    assert isinstance(result.requires_human_review, bool)
    assert result.disclaimer


def test_class_probabilities_sum_to_one():
    result = _make_use_case().execute(_make_request())
    total = sum(result.class_probabilities.values())
    assert abs(total - 1.0) < 0.01


def test_stores_both_images():
    storage = _FakeStorage()
    _make_use_case(storage=storage).execute(_make_request())
    assert len(storage.saved) == 2
    categories_saved = {p.split("/")[2] for p in storage.saved}
    assert "petri" in categories_saved
    assert "micro" in categories_saved


def test_rejects_image_exceeding_max_size():
    use_case = _make_use_case(max_bytes=5)
    with pytest.raises(ImageTooLargeError):
        use_case.execute(_make_request())


def test_rejects_invalid_petri_image():
    with pytest.raises(InvalidImageError):
        _make_use_case(validator=_FakeValidator(raise_error=True)).execute(_make_request())


def test_cleans_up_petri_if_micro_storage_fails():
    storage = _FakeStorage(fail_on_category=ImageCategory.MICRO)
    with pytest.raises(OSError):
        _make_use_case(storage=storage).execute(_make_request())
    # The petri file that was saved first must have been deleted.
    assert len(storage.deleted) == 1
    assert "petri" in storage.deleted[0]


def test_upload_id_is_unique_per_call():
    use_case = _make_use_case()
    req = _make_request()
    r1 = use_case.execute(req)
    r2 = use_case.execute(req)
    assert r1.upload_id != r2.upload_id
