from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionTrainingReadinessConfig:
    """Thresholds and policies for evaluating DetectionTrainingRun readiness.

    Never installs dependencies, never queries `pip freeze`, never imports
    `ultralytics`/`torch`, and never queries a GPU via external commands. Any
    "installed"/"GPU configured" requirement can only be reported as
    `blocked_by_environment` when there is no safe way to confirm it — it is
    never actively checked by installing or importing anything.
    """

    require_detection_training_planned: bool = True
    require_bundle_completed: bool = True
    require_quality_gate_passed: bool = True
    require_dataset_yaml: bool = True
    require_yolo_labels: bool = True
    require_minimum_data: bool = True
    min_total_images: int = 10
    min_total_annotations: int = 10
    min_train_images: int = 5
    min_validation_images: int = 2
    min_test_images: int = 2
    min_train_annotations: int = 5
    min_validation_annotations: int = 2
    min_test_annotations: int = 2
    warn_if_copy_images_disabled: bool = True
    require_training_executor: bool = False
    require_ultralytics_installed: bool = False
    require_torch_installed: bool = False
    require_gpu: bool = False
    allow_cpu_training_future: bool = True
    require_external_weights_policy: bool = False
    allow_external_weights: bool = False
    strict_mode: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "min_total_images",
            "min_total_annotations",
            "min_train_images",
            "min_validation_images",
            "min_test_images",
            "min_train_annotations",
            "min_validation_annotations",
            "min_test_annotations",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be >= 0")

    def to_dict(self) -> dict:
        return {
            "require_detection_training_planned": self.require_detection_training_planned,
            "require_bundle_completed": self.require_bundle_completed,
            "require_quality_gate_passed": self.require_quality_gate_passed,
            "require_dataset_yaml": self.require_dataset_yaml,
            "require_yolo_labels": self.require_yolo_labels,
            "require_minimum_data": self.require_minimum_data,
            "min_total_images": self.min_total_images,
            "min_total_annotations": self.min_total_annotations,
            "min_train_images": self.min_train_images,
            "min_validation_images": self.min_validation_images,
            "min_test_images": self.min_test_images,
            "min_train_annotations": self.min_train_annotations,
            "min_validation_annotations": self.min_validation_annotations,
            "min_test_annotations": self.min_test_annotations,
            "warn_if_copy_images_disabled": self.warn_if_copy_images_disabled,
            "require_training_executor": self.require_training_executor,
            "require_ultralytics_installed": self.require_ultralytics_installed,
            "require_torch_installed": self.require_torch_installed,
            "require_gpu": self.require_gpu,
            "allow_cpu_training_future": self.allow_cpu_training_future,
            "require_external_weights_policy": self.require_external_weights_policy,
            "allow_external_weights": self.allow_external_weights,
            "strict_mode": self.strict_mode,
        }
