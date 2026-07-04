from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LocalYoloTrainingRunnerConfig:
    """Configuration for the local/manual YOLO runner.

    This config is intentionally strict: training is local only, requires an
    exact manual confirmation string, rejects CI, and requires a local base
    model path by default so the runner never downloads weights implicitly.
    """

    manual_confirmation_text: str
    artifact_root_dir: str
    base_model_path: str
    dataset_yaml_path: Optional[str] = None
    run_name: Optional[str] = None
    epochs: Optional[int] = None
    image_size: Optional[int] = None
    batch_size: Optional[int] = None
    device: Optional[str] = None
    workers: Optional[int] = None
    seed: Optional[int] = None
    patience: Optional[int] = None
    allow_existing_output_dir: bool = False
    require_policy_allows_actual_registration: bool = True
    required_confirmation_text: str = "I confirm local YOLO training outside CI"

    def __post_init__(self) -> None:
        if not self.manual_confirmation_text:
            raise ValueError("manual_confirmation_text is required")
        if not self.artifact_root_dir:
            raise ValueError("artifact_root_dir is required")
        if not self.base_model_path:
            raise ValueError("base_model_path is required")
        for field_name in ("epochs", "image_size", "batch_size"):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                raise ValueError(f"{field_name} must be > 0 when provided")
        if self.workers is not None and self.workers < 0:
            raise ValueError("workers must be >= 0 when provided")

    def to_dict(self) -> dict:
        return {
            "manual_confirmation_text_present": bool(self.manual_confirmation_text),
            "artifact_root_dir": self.artifact_root_dir,
            "base_model_path": self.base_model_path,
            "dataset_yaml_path": self.dataset_yaml_path,
            "run_name": self.run_name,
            "epochs": self.epochs,
            "image_size": self.image_size,
            "batch_size": self.batch_size,
            "device": self.device,
            "workers": self.workers,
            "seed": self.seed,
            "patience": self.patience,
            "allow_existing_output_dir": self.allow_existing_output_dir,
            "require_policy_allows_actual_registration": self.require_policy_allows_actual_registration,
        }
