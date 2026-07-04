from __future__ import annotations

import ast
import shutil
from pathlib import Path

from scripts.check_training_docs import validate_docs

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOCS_DIR = _REPO_ROOT / "docs" / "training"
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "check_training_docs.py"


def _copy_training_docs(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    docs_dir = repo / "docs" / "training"
    docs_dir.mkdir(parents=True)
    for source in _DOCS_DIR.iterdir():
        if source.is_file():
            shutil.copy2(source, docs_dir / source.name)
    return repo


def test_training_docs_validator_passes_with_real_documentation():
    assert validate_docs(_REPO_ROOT) == []


def test_training_docs_validator_fails_if_document_is_missing(tmp_path):
    repo = _copy_training_docs(tmp_path)
    (repo / "docs" / "training" / "operator_checklist.md").unlink()

    errors = validate_docs(repo)

    assert any("operator_checklist.md" in error for error in errors)


def test_training_docs_validator_fails_if_runbook_section_is_missing(tmp_path):
    repo = _copy_training_docs(tmp_path)
    runbook = repo / "docs" / "training" / "manual_training_runbook.md"
    runbook.write_text(runbook.read_text(encoding="utf-8").replace("## 6. Environment Validation", ""), encoding="utf-8")

    errors = validate_docs(repo)

    assert any("Environment Validation" in error for error in errors)


def test_training_docs_validator_fails_if_checklist_has_no_checkboxes(tmp_path):
    repo = _copy_training_docs(tmp_path)
    checklist = repo / "docs" / "training" / "operator_checklist.md"
    checklist.write_text(checklist.read_text(encoding="utf-8").replace("- [ ]", "-"), encoding="utf-8")

    errors = validate_docs(repo)

    assert any("checkboxes" in error for error in errors)


def test_training_docs_validator_fails_if_artifact_protocol_lacks_checksum(tmp_path):
    repo = _copy_training_docs(tmp_path)
    protocol = repo / "docs" / "training" / "artifact_registration_protocol.md"
    protocol.write_text(protocol.read_text(encoding="utf-8").replace("checksum_sha256", "checksum"), encoding="utf-8")

    errors = validate_docs(repo)

    assert any("checksum_sha256" in error for error in errors)


def test_training_docs_validator_fails_if_prohibited_actions_lacks_weights_in_git(tmp_path):
    repo = _copy_training_docs(tmp_path)
    prohibited = repo / "docs" / "training" / "prohibited_actions.md"
    text = prohibited.read_text(encoding="utf-8")
    text = text.replace("Do not upload weights to Git.", "Do not upload binaries.")
    text = text.replace("Do not store weights in the repository.", "Do not store binaries locally.")
    prohibited.write_text(text, encoding="utf-8")

    errors = validate_docs(repo)

    assert any("weights in Git" in error for error in errors)


def test_training_docs_validator_does_not_import_torch_or_ultralytics():
    source = _SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert "torch" not in imported_modules
    assert "ultralytics" not in imported_modules


def test_training_docs_validator_does_not_import_subprocess():
    source = _SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert "subprocess" not in imported_modules


def test_training_docs_validator_does_not_modify_files(tmp_path):
    repo = _copy_training_docs(tmp_path)
    before = {
        path.relative_to(repo): path.read_text(encoding="utf-8")
        for path in (repo / "docs" / "training").iterdir()
        if path.is_file()
    }

    validate_docs(repo)

    after = {
        path.relative_to(repo): path.read_text(encoding="utf-8")
        for path in (repo / "docs" / "training").iterdir()
        if path.is_file()
    }
    assert after == before
