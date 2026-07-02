"""SQLite fixtures for repository integration tests.

PostgreSQL is the real target database for this project (see
ARCHITECTURE.md). SQLite is used here only to exercise the SQLAlchemy
repositories against a real engine/session without standing up a Postgres
instance in CI. Every table is included, including `predictions`: its
`class_probabilities` column uses `PortableJSON` (Fase 4), which resolves to
`JSONB` on PostgreSQL and generic `JSON` everywhere else — no table needs to
be excluded anymore.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from blueberry_microid.infrastructure.db.models import (
    AnalysisRunModel,
    Base,
    HumanReviewModel,
    MicroImageModel,
    ModelVersionModel,
    PetriImageModel,
    PredictionModel,
    SampleModel,
)

_SQLITE_TABLES = [
    SampleModel.__table__,
    ModelVersionModel.__table__,
    PetriImageModel.__table__,
    MicroImageModel.__table__,
    AnalysisRunModel.__table__,
    HumanReviewModel.__table__,
    PredictionModel.__table__,
]


@pytest.fixture()
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_SQLITE_TABLES)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(sqlite_engine):
    with Session(sqlite_engine) as session:
        yield session
