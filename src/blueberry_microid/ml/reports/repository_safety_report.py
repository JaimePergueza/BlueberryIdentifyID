from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RepositoryPathViolation:
    """A candidate artifact path that would land inside the repository with
    a forbidden extension. Never the artifact's binary content."""

    path: str
    extension: str
    reason: str


@dataclass(frozen=True, slots=True)
class RepositorySafetyReport:
    is_safe: bool
    gitignore_exists: bool
    missing_gitignore_patterns: list[str] = field(default_factory=list)
    path_violations: list[RepositoryPathViolation] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "gitignore_exists": self.gitignore_exists,
            "missing_gitignore_patterns": list(self.missing_gitignore_patterns),
            "path_violations": [
                {"path": v.path, "extension": v.extension, "reason": v.reason} for v in self.path_violations
            ],
            "recommendations": list(self.recommendations),
        }
