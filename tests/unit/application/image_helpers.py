from io import BytesIO

from PIL import Image


def make_valid_jpeg_bytes(width: int = 32, height: int = 24, color: str = "blue") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=color).save(buffer, format="JPEG")
    return buffer.getvalue()
