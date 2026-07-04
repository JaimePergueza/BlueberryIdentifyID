from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from scripts import seed_local_training_fixture as seed_script


def _outside(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.mkdir()
    return path


def test_dry_run_emits_expected_json_without_persisting(tmp_path, capsys):
    artifact_root = _outside(tmp_path, "artifacts")
    storage_root = _outside(tmp_path, "storage")

    exit_code = seed_script.main(
        [
            "--artifact-root-dir",
            str(artifact_root),
            "--storage-root-dir",
            str(storage_root),
            "--dry-run",
            "--emit-json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    for key in seed_script.SUMMARY_KEYS:
        assert key in payload
    assert payload["would_persist"] is False
    assert payload["would_train"] is False
    assert payload["fixture_kind"] == "synthetic_technical_smoke_fixture"
    assert payload["sample_id"] is None


def test_blocks_artifact_root_inside_repository(tmp_path):
    with pytest.raises(seed_script.LocalTrainingFixtureError, match="artifact_root_dir must be outside"):
        seed_script.main(
            [
                "--artifact-root-dir",
                str(seed_script.REPO_ROOT / "runs"),
                "--storage-root-dir",
                str(tmp_path / "storage"),
                "--dry-run",
            ]
        )


def test_blocks_storage_root_inside_repository(tmp_path):
    with pytest.raises(seed_script.LocalTrainingFixtureError, match="storage_root_dir must be outside"):
        seed_script.main(
            [
                "--artifact-root-dir",
                str(tmp_path / "artifacts"),
                "--storage-root-dir",
                str(seed_script.REPO_ROOT / "storage"),
                "--dry-run",
            ]
        )


def test_dry_run_does_not_create_weights_or_runtime_files(tmp_path, capsys):
    artifact_root = tmp_path / "artifacts"
    storage_root = tmp_path / "storage"

    seed_script.main(
        [
            "--artifact-root-dir",
            str(artifact_root),
            "--storage-root-dir",
            str(storage_root),
            "--dry-run",
            "--emit-json",
        ]
    )
    capsys.readouterr()

    assert not artifact_root.exists()
    assert not storage_root.exists()
    assert list(tmp_path.rglob("*.pt")) == []
    assert list(tmp_path.rglob("*.pth")) == []


def test_script_does_not_import_training_or_process_execution_modules():
    source = Path(seed_script.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert "ultralytics" not in imports
    assert "torch" not in imports
    assert "subprocess" not in imports
    assert "requests" not in imports
