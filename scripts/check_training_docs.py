from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = {
    "manual_training_runbook.md": [
        "## 1. Purpose",
        "## 2. Scope",
        "## 3. What This Document Does Not Permit",
        "## 4. Mandatory Prerequisites",
        "## 5. Gates That Must Be Approved",
        "## 6. Environment Validation",
        "## 7. Repository Validation",
        "## 8. External artifact_root_dir Validation",
        "## 9. Interpreting command_preview",
        "## 10. Pre-Training Checklist",
        "## 11. Evidence Registration",
        "## 12. Post-Training Artifact Registration",
        "## 13. Error Handling",
        "## 14. Rollback",
        "## 15. Prohibited Actions",
        "## 16. Procedure Closure",
    ],
    "operator_checklist.md": ["## Required Checks", "## Criteria To Not Continue", "## Evidence To Record"],
    "artifact_registration_protocol.md": [
        "## Purpose",
        "## Future Artifact Types",
        "## Do Not Store In The Database",
        "## Metadata To Store",
        "## checksum_sha256",
        "## Failed Artifacts",
        "## Deleted Artifacts",
        "## External Artifact Root",
        "## Git Safety",
    ],
    "rollback_protocol.md": [
        "## Purpose",
        "## If Future Training Fails",
        "## Incomplete Weights",
        "## Artifact Inside Repository",
        "## Broken artifact_root_dir",
        "## Dataset Mismatch",
        "## Invalid Metrics",
        "## Incorrect Labels",
        "## Deleted Or Ignored Artifacts",
        "## Incident Documentation",
    ],
    "prohibited_actions.md": ["## Execution And Dependencies", "## Artifacts", "## Data And Labels"],
    "README.md": ["## Reading Order", "## Current Boundary"],
}

REQUIRED_GATES = [
    "AnnotationBundleRun",
    "AnnotationQualityGateRun",
    "DetectionTrainingRun",
    "DetectionTrainingReadinessReport",
    "DetectionTrainingEnvironmentSpec",
    "DetectionTrainingArtifactPolicy",
    "RepositorySafetyValidator",
    "DetectionTrainingExecutionRun",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_docs(repo_root: Path) -> list[str]:
    docs_dir = repo_root / "docs" / "training"
    errors: list[str] = []
    contents: dict[str, str] = {}

    for filename, required_sections in REQUIRED_DOCS.items():
        path = docs_dir / filename
        if not path.is_file():
            errors.append(f"missing document: docs/training/{filename}")
            continue
        text = _read(path)
        contents[filename] = text
        for section in required_sections:
            if section not in text:
                errors.append(f"missing section in {filename}: {section}")

    runbook = contents.get("manual_training_runbook.md", "")
    for gate in REQUIRED_GATES:
        if gate not in runbook:
            errors.append(f"manual_training_runbook.md missing gate: {gate}")
    if "command_preview" not in runbook:
        errors.append("manual_training_runbook.md must mention command_preview")

    checklist = contents.get("operator_checklist.md", "")
    if "- [ ]" not in checklist:
        errors.append("operator_checklist.md must contain Markdown checkboxes")

    artifact_protocol = contents.get("artifact_registration_protocol.md", "")
    if "checksum_sha256" not in artifact_protocol:
        errors.append("artifact_registration_protocol.md must mention checksum_sha256")

    rollback_protocol = contents.get("rollback_protocol.md", "").lower()
    if "rollback" not in rollback_protocol or "failed artifacts" not in rollback_protocol:
        errors.append("rollback_protocol.md must mention rollback and failed artifacts")

    prohibited = contents.get("prohibited_actions.md", "").lower()
    if "do not train in ci" not in prohibited:
        errors.append("prohibited_actions.md must prohibit training in CI")
    if "do not upload weights to git" not in prohibited and "do not store weights in the repository" not in prohibited:
        errors.append("prohibited_actions.md must prohibit weights in Git")

    readme = contents.get("README.md", "").lower()
    if "local/manual" not in readme or "ci still does not train" not in readme:
        errors.append("docs/training/README.md must say training is local/manual only and not in CI")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Fase 30 training operation docs. Read-only; never trains or modifies files."
    )
    parser.add_argument("--repo-root", default=str(_REPO_ROOT), help="Repository root to validate.")
    args = parser.parse_args(argv)

    errors = validate_docs(Path(args.repo_root))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("training docs validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
