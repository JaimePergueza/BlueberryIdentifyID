from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from scripts import inspect_local_training_fixture as inspect_script


def test_fails_if_execution_run_id_is_missing():
    with pytest.raises(SystemExit) as exc_info:
        inspect_script.main([])

    assert exc_info.value.code == 2


def test_fails_clearly_if_database_is_unreachable(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://blueberry:blueberry@localhost:1/blueberry_microid")
    monkeypatch.setattr(
        inspect_script,
        "create_engine",
        lambda _: (_ for _ in ()).throw(OperationalError("select 1", {}, RuntimeError("connection refused"))),
    )

    exit_code = inspect_script.main(["--execution-run-id", "00000000-0000-0000-0000-000000000000"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "could not connect to database" in captured.err
    assert "blueberry:***" in captured.err


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
