"""Fixtures for API tests.

PostgreSQL is the real target database for this project (see
ARCHITECTURE.md). These tests instead point a freshly built `create_app()`
at an in-memory SQLite database (shared across the whole test via
`StaticPool`, since plain `sqlite:///:memory:` would otherwise open a new,
empty database per connection) and at a temporary directory for image
storage. This is fast and hermetic for API-level testing, but it does not
replace validating the real schema against PostgreSQL.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.models import (
    AnalysisRunModel,
    Base,
    DatasetItemModel,
    DatasetReleaseModel,
    DatasetSnapshotModel,
    DatasetSplitItemModel,
    HumanReviewModel,
    ImageDatasetAuditIssueModel,
    ImageDatasetAuditRunModel,
    ImageFeatureExtractionRunModel,
    ImageFeatureVectorModel,
    MicroImageModel,
    ModelVersionModel,
    PetriImageModel,
    PredictionModel,
    SampleModel,
    TrainingPreflightIssueModel,
    TrainingPreflightRunModel,
    TrainingPredictionModel,
    TrainingRunModel,
    TrainingRunComparisonEntryModel,
    TrainingRunComparisonModel,
)
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.interfaces.api.app import create_app

_SQLITE_TABLES = [
    SampleModel.__table__,
    ModelVersionModel.__table__,
    PetriImageModel.__table__,
    MicroImageModel.__table__,
    AnalysisRunModel.__table__,
    HumanReviewModel.__table__,
    PredictionModel.__table__,
    DatasetSnapshotModel.__table__,
    DatasetItemModel.__table__,
    DatasetReleaseModel.__table__,
    DatasetSplitItemModel.__table__,
    TrainingPreflightRunModel.__table__,
    TrainingPreflightIssueModel.__table__,
    TrainingRunModel.__table__,
    TrainingPredictionModel.__table__,
    TrainingRunComparisonModel.__table__,
    TrainingRunComparisonEntryModel.__table__,
    ImageDatasetAuditRunModel.__table__,
    ImageDatasetAuditIssueModel.__table__,
    ImageFeatureExtractionRunModel.__table__,
    ImageFeatureVectorModel.__table__,
]


@pytest.fixture()
def api_client(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=_SQLITE_TABLES)

    app = create_app()
    # Overriding app.state after create_app() — rather than relying on the
    # real DATABASE_URL/storage_root from the environment — is what makes
    # this test isolated and independent of whether PostgreSQL is running.
    app.state.settings = Settings(_env_file=None, storage_root=tmp_path, database_url="sqlite://")
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # raise_server_exceptions=False lets a genuinely unmapped exception come
    # back as an HTTP 500 response instead of propagating as a Python
    # exception inside the test — matching how a real ASGI server behaves.
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    engine.dispose()
