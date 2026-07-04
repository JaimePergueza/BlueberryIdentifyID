from __future__ import annotations

from dataclasses import dataclass, field

from blueberry_microid.ml.configs.training_safety_defaults import (
    default_forbidden_extensions,
    default_required_gitignore_patterns,
)


@dataclass(frozen=True)
class RepositorySafetyConfig:
    """Standalone repository-hygiene policy: which weight/model extensions
    and training-output directories must never be tracked by Git.

    Deliberately reuses the same defaults as
    `DetectionTrainingArtifactPolicyConfig` so the two checks (per-policy
    evaluation vs. whole-repository scan) never disagree about what counts
    as a forbidden pattern. Never modifies `.gitignore` or any file — it
    only reads and reports.
    """

    required_gitignore_patterns: list[str] = field(default_factory=default_required_gitignore_patterns)
    forbidden_extensions: list[str] = field(default_factory=default_forbidden_extensions)

    def to_dict(self) -> dict:
        return {
            "required_gitignore_patterns": list(self.required_gitignore_patterns),
            "forbidden_extensions": list(self.forbidden_extensions),
        }
