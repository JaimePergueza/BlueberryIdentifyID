import logging
from uuid import UUID

from blueberry_microid.application.exceptions import AnalysisProcessingError, DuplicatePredictionError
from blueberry_microid.application.use_cases.inference.process_analysis_run import ProcessAnalysisRunUseCase
from blueberry_microid.domain.exceptions.errors import InvalidAnalysisRunTransitionError
from blueberry_microid.infrastructure.config.settings import Settings, get_settings
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_analysis_run_repository import (
    SqlAlchemyAnalysisRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_micro_image_repository import (
    SqlAlchemyMicroImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_model_version_repository import (
    SqlAlchemyModelVersionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_image_repository import (
    SqlAlchemyPetriImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_prediction_repository import (
    SqlAlchemyPredictionRepository,
)
from blueberry_microid.infrastructure.db.session.engine import create_db_engine
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from blueberry_microid.infrastructure.tasks.celery_app import celery_app
from blueberry_microid.ml.inference_engine.mock_inference_engine import MockInferenceEngine

logger = logging.getLogger("blueberry_microid.tasks.analysis")


def build_process_analysis_run_use_case(settings: Settings | None = None) -> ProcessAnalysisRunUseCase:
    """Build the processing use case without relying on FastAPI dependencies."""
    resolved = settings or get_settings()
    engine = create_db_engine(resolved.database_url)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        use_case = ProcessAnalysisRunUseCase(
            analysis_run_repository=SqlAlchemyAnalysisRunRepository(session),
            petri_image_repository=SqlAlchemyPetriImageRepository(session),
            micro_image_repository=SqlAlchemyMicroImageRepository(session),
            model_version_repository=SqlAlchemyModelVersionRepository(session),
            inference_engine=MockInferenceEngine(),
            unit_of_work=SqlAlchemyUnitOfWork(session_factory),
        )
        # The task owns this infrastructure because it is not running inside
        # FastAPI's request lifecycle. Attach it for a deterministic close in
        # `process_analysis_run_task` without changing the use case API.
        use_case._task_session = session  # type: ignore[attr-defined]
        use_case._task_engine = engine  # type: ignore[attr-defined]
        return use_case
    except Exception:
        session.close()
        engine.dispose()
        raise


def _read_run_status(analysis_run_id: UUID, settings: Settings | None = None) -> str | None:
    resolved = settings or get_settings()
    engine = create_db_engine(resolved.database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        run = SqlAlchemyAnalysisRunRepository(session).get_by_id(analysis_run_id)
        return run.status.value if run is not None else None


@celery_app.task(name="blueberry_microid.infrastructure.tasks.analysis_tasks.process_analysis_run_task")
def process_analysis_run_task(analysis_run_id: str) -> dict[str, str | bool | None]:
    logger.info("async analysis processing started", extra={"analysis_run_id": analysis_run_id})
    try:
        parsed_id = UUID(analysis_run_id)
    except ValueError:
        logger.warning("invalid analysis_run_id for async processing", extra={"analysis_run_id": analysis_run_id})
        raise

    use_case = build_process_analysis_run_use_case()
    try:
        result = use_case.execute(parsed_id)
    except AnalysisProcessingError:
        status = _read_run_status(parsed_id)
        logger.info(
            "async analysis processing finished as failed",
            extra={"analysis_run_id": str(parsed_id), "status": status},
        )
        return {
            "analysis_run_id": str(parsed_id),
            "status": status or "failed",
            "prediction_id": None,
            "mock": True,
        }
    except (DuplicatePredictionError, InvalidAnalysisRunTransitionError):
        status = _read_run_status(parsed_id)
        logger.info(
            "async analysis processing skipped by existing state",
            extra={"analysis_run_id": str(parsed_id), "status": status},
        )
        return {
            "analysis_run_id": str(parsed_id),
            "status": status,
            "prediction_id": None,
            "mock": True,
        }
    except Exception:
        logger.exception("async analysis processing crashed", extra={"analysis_run_id": str(parsed_id)})
        raise
    finally:
        task_session = getattr(use_case, "_task_session", None)
        task_engine = getattr(use_case, "_task_engine", None)
        if task_session is not None:
            task_session.close()
        if task_engine is not None:
            task_engine.dispose()

    response = {
        "analysis_run_id": str(result.analysis_run.id),
        "status": result.analysis_run.status.value,
        "prediction_id": str(result.prediction.id) if result.prediction else None,
        "mock": True,
    }
    logger.info(
        "async analysis processing finished",
        extra={
            "analysis_run_id": response["analysis_run_id"],
            "status": response["status"],
            "prediction_id": response["prediction_id"],
        },
    )
    return response
