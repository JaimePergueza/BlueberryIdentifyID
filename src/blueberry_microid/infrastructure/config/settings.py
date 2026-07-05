from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchored to the installed package location (not the process's current
# working directory), so running the app/tests from an arbitrary directory
# never silently creates/reads a "storage" folder somewhere unexpected.
# This is a computed path, not a hardcoded absolute one — it still resolves
# correctly if the repository is cloned anywhere.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_STORAGE_ROOT = _REPO_ROOT / "storage"


class Settings(BaseSettings):
    """Environment-driven configuration for BlueberryMicroID.

    Values are read from real environment variables first, falling back to
    a local `.env` file (see `.env.example`), falling back to the defaults
    below. Defaults are safe for local development only — they are not
    secrets and must never be used in a deployed environment.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development")
    database_url: str = Field(
        default="postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid"
    )
    storage_root: Path = Field(default=_DEFAULT_STORAGE_ROOT)
    petri_image_dir: str = Field(default="petri_images")
    micro_image_dir: str = Field(default="micro_images")
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="console", description="'json' or 'console'.")
    api_base_url: str = Field(default="http://127.0.0.1:8000")
    max_upload_size_mb: float = Field(
        default=20.0,
        description="Maximum accepted size, in megabytes, for a single Petri/micro image upload.",
    )
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")
    celery_task_always_eager: bool = Field(default=False)
    celery_task_eager_propagates: bool = Field(default=True)
    celery_task_time_limit: int | None = Field(default=300)
    celery_task_soft_time_limit: int | None = Field(default=240)
    upload_storage_dir: Path | None = Field(
        default=None,
        validation_alias="BLUEBERRY_MICROID_UPLOAD_STORAGE_DIR",
    )

    @property
    def upload_storage_path(self) -> Path:
        """Resolved upload storage directory.

        Defaults to ``storage_root / 'uploads'`` so tests that override
        ``storage_root`` (via ``Settings(storage_root=tmp_path)``) automatically
        get an upload dir inside their tmp sandbox without extra config.
        Override explicitly via the ``BLUEBERRY_MICROID_UPLOAD_STORAGE_DIR``
        environment variable.
        """
        return self.upload_storage_dir if self.upload_storage_dir is not None else self.storage_root / "uploads"

    @property
    def petri_image_path(self) -> Path:
        return self.storage_root / self.petri_image_dir

    @property
    def micro_image_path(self) -> Path:
        return self.storage_root / self.micro_image_dir

    @property
    def max_upload_size_bytes(self) -> int:
        return int(self.max_upload_size_mb * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached Settings instance.

    Tests that need different values should construct `Settings(...)`
    directly instead of calling this (bypassing the cache), e.g.
    `Settings(database_url="sqlite:///:memory:")`.
    """
    return Settings()
