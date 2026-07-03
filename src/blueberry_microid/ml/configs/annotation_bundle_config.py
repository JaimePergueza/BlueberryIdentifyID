from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AnnotationBundleConfig:
    output_dir: Optional[str] = None
    dry_run: bool = True
    copy_images: bool = False
    overwrite_existing: bool = False
    include_coco: bool = True
    include_yolo: bool = True
    include_blueberry_manifest: bool = True
    include_dataset_yaml: bool = True
    include_readme: bool = True
    validate_before_write: bool = True
    fail_on_invalid_bbox: bool = True
    fail_on_missing_image: bool = False
    preserve_split_dirs: bool = True
    bundle_name: Optional[str] = None
    relative_image_paths: bool = True

    def __post_init__(self) -> None:
        if self.copy_images:
            raise ValueError("copy_images=true is not_supported_yet for annotation bundles")
        if not self.dry_run and not self.output_dir:
            raise ValueError("output_dir is required when dry_run=false")
        if self.bundle_name is not None and not self.bundle_name.strip():
            raise ValueError("bundle_name must not be blank when provided")

    def to_dict(self) -> dict:
        return {
            "output_dir": self.output_dir,
            "dry_run": self.dry_run,
            "copy_images": self.copy_images,
            "overwrite_existing": self.overwrite_existing,
            "include_coco": self.include_coco,
            "include_yolo": self.include_yolo,
            "include_blueberry_manifest": self.include_blueberry_manifest,
            "include_dataset_yaml": self.include_dataset_yaml,
            "include_readme": self.include_readme,
            "validate_before_write": self.validate_before_write,
            "fail_on_invalid_bbox": self.fail_on_invalid_bbox,
            "fail_on_missing_image": self.fail_on_missing_image,
            "preserve_split_dirs": self.preserve_split_dirs,
            "bundle_name": self.bundle_name,
            "relative_image_paths": self.relative_image_paths,
        }
