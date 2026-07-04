from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from blueberry_microid.ml.configs.training_safety_defaults import (
    default_forbidden_extensions,
    default_required_gitignore_patterns,
)


def _default_forbidden_extensions() -> list[str]:
    return default_forbidden_extensions()


def _default_allowed_metadata_extensions() -> list[str]:
    return [".json", ".yaml", ".yml", ".txt", ".csv", ".md"]


def _default_required_gitignore_patterns() -> list[str]:
    return default_required_gitignore_patterns()


def _default_allowed_external_uri_schemes() -> list[str]:
    return []


@dataclass(frozen=True)
class DetectionTrainingArtifactPolicyConfig:
    """Policy for specifying/validating where future real training
    artifacts would be stored.

    Never creates `artifact_root_dir`, never writes artifact files, never
    computes checksums of real weights (none should exist yet), and never
    modifies `.gitignore` — it only validates and recommends.
    """

    artifact_root_dir: Optional[str] = None
    require_artifact_root_dir: bool = True
    allow_artifacts_inside_repo: bool = False
    allow_artifacts_outside_repo: bool = True
    allow_external_uri: bool = False
    allowed_external_uri_schemes: list[str] = field(default_factory=_default_allowed_external_uri_schemes)
    forbidden_extensions: list[str] = field(default_factory=_default_forbidden_extensions)
    allowed_metadata_extensions: list[str] = field(default_factory=_default_allowed_metadata_extensions)
    require_gitignore_rules: bool = True
    required_gitignore_patterns: list[str] = field(default_factory=_default_required_gitignore_patterns)
    require_checksums_for_actual_artifacts: bool = True
    checksum_algorithm: str = "sha256"
    max_artifact_size_mb: Optional[float] = None
    allow_actual_artifact_registration: bool = False
    register_planned_artifacts: bool = True
    register_actual_artifacts: bool = False
    allow_missing_planned_paths: bool = True
    strict_mode: bool = False
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.max_artifact_size_mb is not None and self.max_artifact_size_mb < 0:
            raise ValueError("max_artifact_size_mb must be >= 0")

    def to_dict(self) -> dict:
        return {
            "artifact_root_dir": self.artifact_root_dir,
            "require_artifact_root_dir": self.require_artifact_root_dir,
            "allow_artifacts_inside_repo": self.allow_artifacts_inside_repo,
            "allow_artifacts_outside_repo": self.allow_artifacts_outside_repo,
            "allow_external_uri": self.allow_external_uri,
            "allowed_external_uri_schemes": list(self.allowed_external_uri_schemes),
            "forbidden_extensions": list(self.forbidden_extensions),
            "allowed_metadata_extensions": list(self.allowed_metadata_extensions),
            "require_gitignore_rules": self.require_gitignore_rules,
            "required_gitignore_patterns": list(self.required_gitignore_patterns),
            "require_checksums_for_actual_artifacts": self.require_checksums_for_actual_artifacts,
            "checksum_algorithm": self.checksum_algorithm,
            "max_artifact_size_mb": self.max_artifact_size_mb,
            "allow_actual_artifact_registration": self.allow_actual_artifact_registration,
            "register_planned_artifacts": self.register_planned_artifacts,
            "register_actual_artifacts": self.register_actual_artifacts,
            "allow_missing_planned_paths": self.allow_missing_planned_paths,
            "strict_mode": self.strict_mode,
            "notes": self.notes,
        }
