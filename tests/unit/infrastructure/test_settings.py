import os

import pytest

from blueberry_microid.infrastructure.config.settings import Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    # Settings reads real env vars first; scrub the ones this test suite
    # cares about so tests don't depend on whatever the host shell has set.
    for key in (
        "ENVIRONMENT",
        "DATABASE_URL",
        "STORAGE_ROOT",
        "PETRI_IMAGE_DIR",
        "MICRO_IMAGE_DIR",
        "LOG_LEVEL",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
        "CELERY_TASK_ALWAYS_EAGER",
        "CELERY_TASK_EAGER_PROPAGATES",
    ):
        monkeypatch.delenv(key, raising=False)


def test_settings_have_safe_local_defaults():
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.petri_image_dir == "petri_images"
    assert settings.micro_image_dir == "micro_images"
    assert settings.celery_broker_url == "redis://localhost:6379/0"
    assert settings.celery_result_backend == "redis://localhost:6379/1"
    assert settings.celery_task_always_eager is False
    assert settings.celery_task_eager_propagates is True
    # The default must not depend on the process's current working directory.
    assert settings.storage_root.is_absolute()


def test_settings_default_storage_paths_are_separated():
    settings = Settings(_env_file=None)

    assert settings.petri_image_path != settings.micro_image_path
    assert settings.petri_image_path.name == "petri_images"
    assert settings.micro_image_path.name == "micro_images"


def test_settings_read_from_environment_variables(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/testdb")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://redis:6379/3")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://redis:6379/4")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")

    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/testdb"
    assert settings.celery_broker_url == "redis://redis:6379/3"
    assert settings.celery_result_backend == "redis://redis:6379/4"
    assert settings.celery_task_always_eager is True


def test_settings_can_be_overridden_explicitly_for_tests():
    settings = Settings(_env_file=None, database_url="sqlite:///:memory:")

    assert settings.database_url == "sqlite:///:memory:"
