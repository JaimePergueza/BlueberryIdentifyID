from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AnnotationBundleFile:
    """Metadata for one generated or planned bundle file."""

    bundle_run_id: UUID
    file_role: AnnotationBundleFileRole
    file_path: str
    relative_path: str
    id: UUID = field(default_factory=uuid4)
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.file_path:
            raise ValueError("file_path must not be blank")
        if not self.relative_path:
            raise ValueError("relative_path must not be blank")
