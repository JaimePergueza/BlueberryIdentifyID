from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class ImageFeatureExtractionConfig:
    """Configuration for a non-deep ImageFeatureExtractor pass.

    Controls only lightweight Pillow/numpy-based technical feature
    computation over already-audited image files — never a training
    hyperparameter, never PyTorch/TensorFlow settings.
    """

    require_audit_passed: bool = True
    allow_audit_warning: bool = True
    convert_to_rgb: bool = True
    resize_enabled: bool = False
    resize_width: Optional[int] = None
    resize_height: Optional[int] = None
    compute_basic_geometry: bool = True
    compute_intensity_features: bool = True
    compute_color_features: bool = True
    compute_sharpness_features: bool = True
    compute_texture_features: bool = True
    compute_histogram_features: bool = True
    histogram_bins: int = 16
    max_image_pixels: Optional[int] = None
    fail_on_unreadable_image: bool = True

    def __post_init__(self) -> None:
        if self.histogram_bins <= 0:
            raise ValueError("histogram_bins must be > 0")
        if self.resize_enabled:
            if not self.resize_width or self.resize_width <= 0:
                raise ValueError("resize_width must be > 0 when resize_enabled is true")
            if not self.resize_height or self.resize_height <= 0:
                raise ValueError("resize_height must be > 0 when resize_enabled is true")
        if self.max_image_pixels is not None and self.max_image_pixels <= 0:
            raise ValueError("max_image_pixels must be > 0")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageFeatureExtractionConfig":
        return cls(**data)
