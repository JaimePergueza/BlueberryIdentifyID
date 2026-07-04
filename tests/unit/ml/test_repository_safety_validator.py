from pathlib import Path

from blueberry_microid.ml.configs.repository_safety_config import RepositorySafetyConfig
from blueberry_microid.ml.validation.repository_safety_validator import RepositorySafetyValidator

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _config(**overrides) -> RepositorySafetyConfig:
    values = {
        "required_gitignore_patterns": ["*.pt", "*.pth", "runs/"],
        "forbidden_extensions": [".pt", ".pth"],
    }
    values.update(overrides)
    return RepositorySafetyConfig(**values)


def test_reports_safe_when_gitignore_covers_all_patterns(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n*.pth\nruns/\n", encoding="utf-8")

    report = RepositorySafetyValidator().validate(tmp_path, _config())

    assert report.is_safe is True
    assert report.gitignore_exists is True
    assert report.missing_gitignore_patterns == []


def test_reports_missing_gitignore_file(tmp_path):
    report = RepositorySafetyValidator().validate(tmp_path, _config())

    assert report.is_safe is False
    assert report.gitignore_exists is False
    assert report.missing_gitignore_patterns == ["*.pt", "*.pth", "runs/"]
    assert any("create a .gitignore" in rec for rec in report.recommendations)


def test_reports_missing_individual_patterns(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n", encoding="utf-8")

    report = RepositorySafetyValidator().validate(tmp_path, _config())

    assert report.is_safe is False
    assert report.missing_gitignore_patterns == ["*.pth", "runs/"]


def test_ignores_commented_and_blank_lines(tmp_path):
    (tmp_path / ".gitignore").write_text("# comment\n\n*.pt\n*.pth\nruns/\n", encoding="utf-8")

    report = RepositorySafetyValidator().validate(tmp_path, _config())

    assert report.is_safe is True


def test_flags_candidate_path_inside_repo_with_forbidden_extension(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n*.pth\nruns/\n", encoding="utf-8")
    candidate = str(tmp_path / "weights" / "best.pt")

    report = RepositorySafetyValidator().validate(tmp_path, _config(), candidate_paths=[candidate])

    assert report.is_safe is False
    assert len(report.path_violations) == 1
    assert report.path_violations[0].path == candidate
    assert report.path_violations[0].extension == ".pt"


def test_allows_candidate_path_outside_repo(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n*.pth\nruns/\n", encoding="utf-8")
    outside = tmp_path.parent / "outside-artifacts" / "best.pt"

    report = RepositorySafetyValidator().validate(tmp_path, _config(), candidate_paths=[str(outside)])

    assert report.is_safe is True
    assert report.path_violations == []


def test_ignores_candidate_path_with_allowed_extension(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n*.pth\nruns/\n", encoding="utf-8")
    candidate = str(tmp_path / "metrics.json")

    report = RepositorySafetyValidator().validate(tmp_path, _config(), candidate_paths=[candidate])

    assert report.is_safe is True


def test_ignores_external_uri_candidate_paths(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n*.pth\nruns/\n", encoding="utf-8")

    report = RepositorySafetyValidator().validate(
        tmp_path, _config(), candidate_paths=["s3://bucket/weights/best.pt"]
    )

    assert report.is_safe is True


def test_ignores_relative_candidate_paths(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n*.pth\nruns/\n", encoding="utf-8")

    report = RepositorySafetyValidator().validate(tmp_path, _config(), candidate_paths=["relative/best.pt"])

    assert report.is_safe is True


def test_ignores_empty_candidate_paths(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n*.pth\nruns/\n", encoding="utf-8")

    report = RepositorySafetyValidator().validate(tmp_path, _config(), candidate_paths=["", None])

    assert report.is_safe is True


def test_default_config_is_used_when_none_provided(tmp_path):
    (tmp_path / ".gitignore").write_text("", encoding="utf-8")

    report = RepositorySafetyValidator().validate(tmp_path)

    assert report.is_safe is False
    assert "*.pt" in report.missing_gitignore_patterns


def test_never_modifies_gitignore(tmp_path):
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text("*.pt\n", encoding="utf-8")
    original_content = gitignore_path.read_text(encoding="utf-8")

    RepositorySafetyValidator().validate(tmp_path, _config())

    assert gitignore_path.read_text(encoding="utf-8") == original_content


def test_never_writes_new_files(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pt\n*.pth\nruns/\n", encoding="utf-8")

    RepositorySafetyValidator().validate(tmp_path, _config(), candidate_paths=[str(tmp_path / "weights" / "x.pt")])

    assert list(tmp_path.rglob("*")) == [tmp_path / ".gitignore"]


def test_real_repository_gitignore_is_safe():
    report = RepositorySafetyValidator().validate(_REPO_ROOT)

    assert report.gitignore_exists is True
    assert report.missing_gitignore_patterns == []
    assert report.is_safe is True
