from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class PetriSegmentationConfig:
    """Configuration for classical Petri candidate-region segmentation.

    This config controls deterministic OpenCV image processing only:
    grayscale conversion, blur, thresholding, morphology, contours, and
    geometry. It is not a model config and never enables OpenCV DNN, YOLO, or
    a pretrained detector.
    """

    algorithm: str = "classical_threshold"
    convert_to_grayscale: bool = True
    blur_enabled: bool = True
    blur_kernel_size: int = 5
    threshold_method: str = "otsu"
    manual_threshold: Optional[int] = None
    invert_threshold: bool = False
    morphological_opening: bool = True
    morphological_closing: bool = True
    morphology_kernel_size: int = 3
    min_region_area_px: int = 25
    max_region_area_px: Optional[int] = None
    min_circularity: Optional[float] = None
    exclude_border_regions: bool = False
    border_margin_px: int = 5
    max_regions: Optional[int] = None
    save_debug_masks: bool = False
    extraction_version: str = "petri_classical_v1"

    def __post_init__(self) -> None:
        if self.algorithm != "classical_threshold":
            raise ValueError("algorithm must be 'classical_threshold'")
        if self.threshold_method not in {"otsu", "adaptive", "manual"}:
            raise ValueError("threshold_method must be one of: otsu, adaptive, manual")
        if self.blur_kernel_size < 3 or self.blur_kernel_size % 2 == 0:
            raise ValueError("blur_kernel_size must be odd and >= 3")
        if self.morphology_kernel_size < 3 or self.morphology_kernel_size % 2 == 0:
            raise ValueError("morphology_kernel_size must be odd and >= 3")
        if self.min_region_area_px <= 0:
            raise ValueError("min_region_area_px must be > 0")
        if self.max_region_area_px is not None and self.max_region_area_px <= self.min_region_area_px:
            raise ValueError("max_region_area_px must be > min_region_area_px")
        if self.threshold_method == "manual":
            if self.manual_threshold is None:
                raise ValueError("manual_threshold is required when threshold_method='manual'")
            if self.manual_threshold < 0 or self.manual_threshold > 255:
                raise ValueError("manual_threshold must be between 0 and 255")
        if self.min_circularity is not None and self.min_circularity < 0:
            raise ValueError("min_circularity must be >= 0")
        if self.border_margin_px < 0:
            raise ValueError("border_margin_px must be >= 0")
        if self.max_regions is not None and self.max_regions <= 0:
            raise ValueError("max_regions must be > 0")
        if self.save_debug_masks:
            raise ValueError("save_debug_masks is not implemented in this phase")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PetriSegmentationConfig":
        return cls(**data)
