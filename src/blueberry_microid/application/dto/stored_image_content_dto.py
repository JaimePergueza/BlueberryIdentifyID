from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredImageContentDTO:
    """Safe image payload returned by protected content use cases."""

    content: bytes
    file_name: str
    mime_type: str
