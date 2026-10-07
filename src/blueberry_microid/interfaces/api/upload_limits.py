"""Read accepted upload bytes without first allocating the entire file."""

from fastapi import UploadFile

from blueberry_microid.application.exceptions import ImageTooLargeError


async def read_bounded_upload(upload: UploadFile, max_bytes: int) -> bytes:
    if max_bytes <= 0:
        raise ValueError("upload size limit must be positive")
    content = bytearray()
    while True:
        chunk = await upload.read(min(64 * 1024, max_bytes + 1 - len(content)))
        if not chunk:
            return bytes(content)
        content.extend(chunk)
        if len(content) > max_bytes:
            raise ImageTooLargeError("Image exceeds the configured upload size limit")
