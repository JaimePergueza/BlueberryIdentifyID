from io import BytesIO

import pytest
from PIL import Image

from blueberry_microid.application.exceptions import InvalidImageError
from blueberry_microid.infrastructure.storage.pillow_image_validator import PillowImageValidator


def _bytes_for(fmt: str, width: int = 20, height: int = 15) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color="blue").save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture()
def validator() -> PillowImageValidator:
    return PillowImageValidator()


def test_accepts_valid_jpeg(validator):
    content = _bytes_for("JPEG")

    result = validator.validate(file_name="colony.jpg", mime_type="image/jpeg", content=content)

    assert result.width == 20
    assert result.height == 15


def test_accepts_valid_png(validator):
    content = _bytes_for("PNG")

    result = validator.validate(file_name="colony.png", mime_type="image/png", content=content)

    assert result.width == 20
    assert result.height == 15


def test_accepts_valid_tiff(validator):
    content = _bytes_for("TIFF")

    result = validator.validate(file_name="colony.tif", mime_type="image/tiff", content=content)

    assert result.width == 20
    assert result.height == 15


def test_rejects_mime_type_lying_about_real_format(validator):
    """Real content is JPEG, but the declared MIME type says PNG."""
    content = _bytes_for("JPEG")

    with pytest.raises(InvalidImageError, match="does not match the actual image format"):
        validator.validate(file_name="colony.jpg", mime_type="image/png", content=content)


def test_rejects_extension_lying_about_real_format(validator):
    """Real content is JPEG, but the file is named with a .png extension."""
    content = _bytes_for("JPEG")

    with pytest.raises(InvalidImageError, match="does not match the actual image format"):
        validator.validate(file_name="colony.png", mime_type="image/jpeg", content=content)


def test_rejects_when_extension_and_mime_agree_but_both_lie_about_real_format(validator):
    """MIME and extension both claim PNG; the bytes are actually a JPEG."""
    content = _bytes_for("JPEG")

    with pytest.raises(InvalidImageError):
        validator.validate(file_name="colony.png", mime_type="image/png", content=content)


def test_rejects_disallowed_mime_type(validator):
    content = _bytes_for("JPEG")

    with pytest.raises(InvalidImageError, match="mime type"):
        validator.validate(file_name="colony.jpg", mime_type="application/pdf", content=content)


def test_rejects_disallowed_extension(validator):
    content = _bytes_for("JPEG")

    with pytest.raises(InvalidImageError, match="extension"):
        validator.validate(file_name="colony.exe", mime_type="image/jpeg", content=content)


def test_rejects_empty_file(validator):
    with pytest.raises(InvalidImageError, match="empty"):
        validator.validate(file_name="colony.jpg", mime_type="image/jpeg", content=b"")


def test_rejects_corrupted_image(validator):
    with pytest.raises(InvalidImageError, match="corrupted"):
        validator.validate(file_name="colony.jpg", mime_type="image/jpeg", content=b"not-a-real-image")
