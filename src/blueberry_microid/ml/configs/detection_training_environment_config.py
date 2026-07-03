from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DetectionTrainingEnvironmentConfig:
    """Policy for specifying/validating a future real training environment.

    Never installs dependencies, never imports `ultralytics`/`torch`, never
    downloads weights, and never trains anything — even when a `require_*`
    flag is `true`. Those flags only shape which issues the evaluator
    reports; they never trigger an installation or download action.
    """

    target_python_version: Optional[str] = None
    target_os: Optional[str] = None
    allow_cpu_training: bool = True
    require_gpu: bool = False
    require_cuda: bool = False
    target_cuda_version: Optional[str] = None
    require_ultralytics: bool = False
    target_ultralytics_version: Optional[str] = None
    require_torch: bool = False
    target_torch_version: Optional[str] = None
    allow_dependency_installation: bool = False
    allow_external_weights: bool = False
    pretrained_weights_policy: str = "none"
    pretrained_weights_path: Optional[str] = None
    artifact_output_dir: Optional[str] = None
    allow_artifacts_outside_repo: bool = True
    allow_artifacts_inside_repo: bool = False
    max_expected_artifact_size_mb: Optional[float] = None
    allow_ci_training: bool = False
    allow_local_training: bool = True
    require_manual_confirmation: bool = True
    strict_mode: bool = False
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.max_expected_artifact_size_mb is not None and self.max_expected_artifact_size_mb < 0:
            raise ValueError("max_expected_artifact_size_mb must be >= 0")

    def to_dict(self) -> dict:
        return {
            "target_python_version": self.target_python_version,
            "target_os": self.target_os,
            "allow_cpu_training": self.allow_cpu_training,
            "require_gpu": self.require_gpu,
            "require_cuda": self.require_cuda,
            "target_cuda_version": self.target_cuda_version,
            "require_ultralytics": self.require_ultralytics,
            "target_ultralytics_version": self.target_ultralytics_version,
            "require_torch": self.require_torch,
            "target_torch_version": self.target_torch_version,
            "allow_dependency_installation": self.allow_dependency_installation,
            "allow_external_weights": self.allow_external_weights,
            "pretrained_weights_policy": self.pretrained_weights_policy,
            "pretrained_weights_path": self.pretrained_weights_path,
            "artifact_output_dir": self.artifact_output_dir,
            "allow_artifacts_outside_repo": self.allow_artifacts_outside_repo,
            "allow_artifacts_inside_repo": self.allow_artifacts_inside_repo,
            "max_expected_artifact_size_mb": self.max_expected_artifact_size_mb,
            "allow_ci_training": self.allow_ci_training,
            "allow_local_training": self.allow_local_training,
            "require_manual_confirmation": self.require_manual_confirmation,
            "strict_mode": self.strict_mode,
            "notes": self.notes,
        }
