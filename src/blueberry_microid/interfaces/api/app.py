"""FastAPI application factory for BlueberryMicroID.

BlueberryMicroID is a preliminary, non-diagnostic platform. The official MVP
upload endpoint analyzes real Petri and microscopy pixels with transparent,
non-trained classical image-processing rules. Expert review remains mandatory.
"""

from fastapi import Depends, FastAPI

from blueberry_microid.infrastructure.config.settings import get_settings
from blueberry_microid.infrastructure.db.session.engine import create_db_engine
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.logging.config import configure_logging
from blueberry_microid.infrastructure.logging.middleware import RequestLoggingMiddleware
from blueberry_microid.infrastructure.tasks.celery_app import celery_app
from blueberry_microid.interfaces.api.auth_error_handlers import register_auth_exception_handlers
from blueberry_microid.interfaces.api.error_handlers import register_exception_handlers
from blueberry_microid.interfaces.api.security import require_admin, require_specialist
from blueberry_microid.interfaces.api.v1.routers import (
    admin_users,
    analysis,
    analysis_runs,
    annotation_bundles,
    annotation_quality_gates,
    auth,
    datasets,
    detection_training,
    detection_training_artifacts,
    detection_training_environment,
    detection_training_execution,
    detection_training_readiness,
    human_reviews,
    image_audits,
    image_features,
    ml_preflight,
    micro_images,
    model_evaluation,
    model_versions,
    petri_annotation_exports,
    petri_region_reviews,
    petri_segmentations,
    petri_images,
    samples,
    tasks,
    training_run_comparisons,
    training_runs,
)

API_V1_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build a fresh, environment-configured FastAPI application."""
    settings = get_settings()
    configure_logging(settings)
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    docs_url = "/docs" if settings.api_docs_enabled else None
    redoc_url = "/redoc" if settings.api_docs_enabled else None
    openapi_url = "/openapi.json" if settings.api_docs_enabled else None

    app = FastAPI(
        title="BlueberryMicroID",
        description=(
            "Preliminary, non-diagnostic support for analyzing Petri dish and "
            "microscopy images from the same blueberry-associated sample. "
            "The official analysis produces an unvalidated preliminary visual "
            "category and always requires expert review. The API never "
            "identifies microorganism species or genus."
        ),
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.celery_app = celery_app

    app.add_middleware(RequestLoggingMiddleware)

    # Public authentication boundary. /health is registered below.
    app.include_router(auth.router, prefix=API_V1_PREFIX)

    specialist_access = [Depends(require_specialist)]
    app.include_router(analysis.router, prefix=API_V1_PREFIX, dependencies=specialist_access)
    app.include_router(samples.router, prefix=API_V1_PREFIX, dependencies=specialist_access)
    app.include_router(petri_images.router, prefix=API_V1_PREFIX, dependencies=specialist_access)
    app.include_router(micro_images.router, prefix=API_V1_PREFIX, dependencies=specialist_access)
    app.include_router(analysis_runs.router, prefix=API_V1_PREFIX, dependencies=specialist_access)
    app.include_router(human_reviews.router, prefix=API_V1_PREFIX, dependencies=specialist_access)

    admin_access = [Depends(require_admin)]
    app.include_router(admin_users.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(model_versions.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(model_evaluation.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(annotation_bundles.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(annotation_quality_gates.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(datasets.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(ml_preflight.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(training_runs.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(training_run_comparisons.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(image_audits.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(image_features.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(petri_segmentations.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(petri_region_reviews.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(petri_annotation_exports.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(detection_training.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(detection_training_readiness.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(detection_training_environment.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(detection_training_artifacts.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(detection_training_execution.router, prefix=API_V1_PREFIX, dependencies=admin_access)
    app.include_router(tasks.router, prefix=API_V1_PREFIX, dependencies=admin_access)

    register_exception_handlers(app)
    register_auth_exception_handlers(app)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "BlueberryMicroID"}

    return app
