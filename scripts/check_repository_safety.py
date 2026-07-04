from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from blueberry_microid.ml.configs.repository_safety_config import RepositorySafetyConfig
from blueberry_microid.ml.validation.repository_safety_validator import RepositorySafetyValidator

_REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check that .gitignore covers the required weight/model/training-output patterns "
            "before any future real training attempt. Read-only: never modifies .gitignore, never "
            "trains anything, never installs torch/ultralytics."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=str(_REPO_ROOT),
        help="Repository root to check (default: this script's repo root).",
    )
    parser.add_argument(
        "--candidate-path",
        action="append",
        default=[],
        dest="candidate_paths",
        help="An absolute path to check against forbidden extensions/repo location. Repeatable.",
    )
    args = parser.parse_args(argv)

    validator = RepositorySafetyValidator()
    report = validator.validate(
        repo_root=Path(args.repo_root),
        config=RepositorySafetyConfig(),
        candidate_paths=args.candidate_paths,
    )

    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.is_safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
