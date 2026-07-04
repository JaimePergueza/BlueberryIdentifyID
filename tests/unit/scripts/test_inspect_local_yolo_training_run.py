from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts import inspect_local_yolo_training_run as inspect_script


def test_fails_if_run_id_is_missing():
    with pytest.raises(SystemExit) as exc_info:
        inspect_script.main([])

    assert exc_info.value.code == 2


def test_rejects_invalid_uuid(capsys):
    exit_code = inspect_script.main(["--local-training-run-id", "not-a-uuid"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "valid UUID" in captured.err


def test_script_does_not_import_training_modules_or_subprocess():
    source = Path(inspect_script.__file__).read_text(encoding="utf-8")
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
