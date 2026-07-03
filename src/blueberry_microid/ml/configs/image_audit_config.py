from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class ImageAuditConfig:
    """Configuration for a technical ImageDatasetAuditor pass.

    This is deliberately separate from `TrainingConfig`: it only controls
    which lightweight, Pillow-based technical checks run against already
    stored image files, never how a future model would be trained.
    """

    validate_existence: bool = True
    validate_readability: bool = True
    validate_format: bool = True
    validate_dimensions: bool = True
    validate_color_mode: bool = True
    validate_file_size: bool = True
    detect_duplicate_paths: bool = True
    min_width: int = 64
    min_height: int = 64
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    max_file_size_bytes: Optional[int] = None
    allowed_formats: tuple[str, ...] = ("JPEG", "PNG", "WEBP")
    allowed_color_modes: tuple[str, ...] = ("RGB", "RGBA", "L")
    warn_on_dimension_outliers: bool = True

    def __post_init__(self) -> None:
        if self.min_width <= 0:
            raise ValueError("min_width must be > 0")
        if self.min_height <= 0:
            raise ValueError("min_height must be > 0")
        if self.max_width is not None and self.max_width <= self.min_width:
            raise ValueError("max_width must be > min_width")
        if self.max_height is not None and self.max_height <= self.min_height:
            raise ValueError("max_height must be > min_height")
        if self.max_file_size_bytes is not None and self.max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be > 0")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageAuditConfig":
        payload = dict(data)
        if "allowed_formats" in payload and payload["allowed_formats"] is not None:
            payload["allowed_formats"] = tuple(payload["allowed_formats"])
        if "allowed_color_modes" in payload and payload["allowed_color_modes"] is not None:
            payload["allowed_color_modes"] = tuple(payload["allowed_color_modes"])
        return cls(**payload)
