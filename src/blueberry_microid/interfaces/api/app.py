"""FastAPI application factory for BlueberryMicroID.

This API is a preliminary, non-diagnostic tool: its inference endpoint uses
only a deterministic mock engine, and it never identifies microorganism
species/genus. See ARCHITECTURE.md and CLAUDE.md for the full scope
statement.
"""

from fastapi import FastAPI

from blueberry_microid.infrastructure.config.settings import get_settings
from blueberry_microid.infrastructure.db.session.engine import create_db_engine
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.logging.config import configure_logging
from blueberry_microid.infrastructure.logging.middleware import RequestLoggingMiddleware
from blueberry_microid.infrastructure.tasks.celery_app import celery_app
from blueberry_microid.interfaces.api.error_handlers import register_exception_handlers
from blueberry_microid.interfaces.api.v1.routers import (
    analysis_runs,
    datasets,
    human_reviews,
    image_audits,
    ml_preflight,
    micro_images,
    model_versions,
    petri_images,
    samples,
    tasks,
    training_runs,
)

API_V1_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build a fresh FastAPI application.

    A factory function (rather than a module-level `app = FastAPI()`
    global) so tests can construct an isolated app per test and point its
    `app.state.session_factory` / `app.state.settings` at a throwaway
    SQLite database and temp storage directory instead of the real
    PostgreSQL configured by the environment (see tests/api/conftest.py).

    `create_engine()` is lazy in SQLAlchemy — building the engine here does
    not open a connection, so this never fails just because no database is
    reachable yet.
    """
    settings = get_settings()
    configure_logging(settings)
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    app = FastAPI(
        title="BlueberryMicroID",
        description=(
            "Preliminary, non-diagnostic support for recognizing microorganisms "
            "associated with blueberries, from Petri dish (macro) and microscopy "
            "(micro) imagery. The inference endpoint uses only a deterministic "
            "mock engine; human reviews are recorded separately for audit, and "
            "the API does not identify species/genus."
        ),
        version="0.1.0",
    )

    # Every dependency a route needs is resolved from `app.state` at request
    # time (see interfaces/api/v1/dependencies.py) rather than baked into a
    # rigid module-level singleton, precisely so tests can swap them out.
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.celery_app = celery_app

    # Assigns/reads request_id and logs one structured line per request; see
    # infrastructure/logging/middleware.py.
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(samples.router, prefix=API_V1_PREFIX)
    app.include_router(model_versions.router, prefix=API_V1_PREFIX)
    app.include_router(petri_images.router, prefix=API_V1_PREFIX)
    app.include_router(micro_images.router, prefix=API_V1_PREFIX)
    app.include_router(analysis_runs.router, prefix=API_V1_PREFIX)
    app.include_router(human_reviews.router, prefix=API_V1_PREFIX)
    app.include_router(datasets.router, prefix=API_V1_PREFIX)
    app.include_router(ml_preflight.router, prefix=API_V1_PREFIX)
    app.include_router(training_runs.router, prefix=API_V1_PREFIX)
    app.include_router(image_audits.router, prefix=API_V1_PREFIX)
    app.include_router(tasks.router, prefix=API_V1_PREFIX)

    register_exception_handlers(app)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "BlueberryMicroID"}

    return app
