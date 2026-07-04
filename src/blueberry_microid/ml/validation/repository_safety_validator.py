from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from blueberry_microid.ml.configs.repository_safety_config import RepositorySafetyConfig
from blueberry_microid.ml.reports.repository_safety_report import RepositoryPathViolation, RepositorySafetyReport


class RepositorySafetyValidator:
    """Read-only repository-hygiene check: does `.gitignore` cover the
    required weight/model/training-output patterns, and do any candidate
    artifact paths resolve inside the repository with a forbidden
    extension.

    Never modifies `.gitignore`, never writes files, never trains anything,
    never imports `torch`/`ultralytics`. This is a standalone counterpart to
    `DetectionTrainingArtifactPolicyEvaluator`'s git/repo checks: it does not
    require a `DetectionTrainingRun`/`DetectionTrainingArtifactPolicy` graph
    to exist, so it can run as a cheap CI/local gate on its own.
    """

    def validate(
        self,
        repo_root: Path,
        config: Optional[RepositorySafetyConfig] = None,
        candidate_paths: Optional[Iterable[str]] = None,
    ) -> RepositorySafetyReport:
        config = config or RepositorySafetyConfig()
        gitignore_exists, missing_patterns = self._check_gitignore(repo_root, config)
        path_violations = self._check_candidate_paths(repo_root, config, candidate_paths or [])

        is_safe = gitignore_exists and not missing_patterns and not path_violations
        recommendations: list[str] = []
        if not gitignore_exists:
            recommendations.append("create a .gitignore at the repository root")
        elif missing_patterns:
            recommendations.append(f"add missing .gitignore patterns: {', '.join(missing_patterns)}")
        if path_violations:
            recommendations.append("move forbidden-extension artifact paths outside the repository")

        return RepositorySafetyReport(
            is_safe=is_safe,
            gitignore_exists=gitignore_exists,
            missing_gitignore_patterns=missing_patterns,
            path_violations=path_violations,
            recommendations=recommendations,
        )

    @staticmethod
    def _check_gitignore(repo_root: Path, config: RepositorySafetyConfig) -> tuple[bool, list[str]]:
        gitignore_path = repo_root / ".gitignore"
        if not gitignore_path.exists():
            return False, list(config.required_gitignore_patterns)
        try:
            content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""
        lines = {line.strip() for line in content.splitlines()}
        missing = [pattern for pattern in config.required_gitignore_patterns if pattern not in lines]
        return True, missing

    @staticmethod
    def _check_candidate_paths(
        repo_root: Path, config: RepositorySafetyConfig, candidate_paths: Iterable[str]
    ) -> list[RepositoryPathViolation]:
        violations: list[RepositoryPathViolation] = []
        for raw_path in candidate_paths:
            if not raw_path or "://" in raw_path:
                continue
            path = Path(raw_path)
            if not path.is_absolute():
                continue
            extension = path.suffix.lower()
            if extension not in config.forbidden_extensions:
                continue
            if not RepositorySafetyValidator._is_inside(path, repo_root):
                continue
            violations.append(
                RepositoryPathViolation(
                    path=raw_path,
                    extension=extension,
                    reason=f"path resolves inside the repository with forbidden extension '{extension}'",
                )
            )
        return violations

    @staticmethod
    def _is_inside(path: Path, repo_root: Path) -> bool:
        try:
            resolved = path.resolve()
            repo_root_resolved = repo_root.resolve()
        except OSError:
            return False
        try:
            resolved.relative_to(repo_root_resolved)
            return True
        except ValueError:
            return False
