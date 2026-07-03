from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode


@dataclass(frozen=True)
class DetectionTrainingConfig:
    """Configuration for planning a detection training dry-run.

    This never executes anything: `device` defaults to `"cpu"`, no GPU is
    required or checked, `pretrained_weights_path` is never downloaded or
    remotely validated, and `allow_external_weights=true` only registers
    intent (surfaced as a warning) without fetching any weights.
    """

    algorithm: DetectionTrainingAlgorithm = DetectionTrainingAlgorithm.YOLO_DRY_RUN
    mode: DetectionTrainingMode = DetectionTrainingMode.DRY_RUN
    require_quality_gate_passed: bool = True
    require_dataset_yaml: bool = True
    require_yolo_labels: bool = True
    require_coco_annotations: bool = False
    planned_model_family: str = "yolo"
    planned_model_variant: Optional[str] = None
    image_size: int = 640
    epochs: int = 50
    batch_size: int = 8
    patience: Optional[int] = None
    seed: int = 42
    device: str = "cpu"
    workers: int = 0
    allow_external_weights: bool = False
    pretrained_weights_path: Optional[str] = None
    output_dir: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "algorithm", DetectionTrainingAlgorithm(self.algorithm))
        object.__setattr__(self, "mode", DetectionTrainingMode(self.mode))
        if self.image_size <= 0:
            raise ValueError("image_size must be > 0")
        if self.epochs <= 0:
            raise ValueError("epochs must be > 0")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if self.patience is not None and self.patience <= 0:
            raise ValueError("patience must be > 0 when provided")
        if self.workers < 0:
            raise ValueError("workers must be >= 0")

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm.value,
            "mode": self.mode.value,
            "require_quality_gate_passed": self.require_quality_gate_passed,
            "require_dataset_yaml": self.require_dataset_yaml,
            "require_yolo_labels": self.require_yolo_labels,
            "require_coco_annotations": self.require_coco_annotations,
            "planned_model_family": self.planned_model_family,
            "planned_model_variant": self.planned_model_variant,
            "image_size": self.image_size,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "patience": self.patience,
            "seed": self.seed,
            "device": self.device,
            "workers": self.workers,
            "allow_external_weights": self.allow_external_weights,
            "pretrained_weights_path": self.pretrained_weights_path,
            "output_dir": self.output_dir,
            "notes": self.notes,
        }
