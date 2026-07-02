from celery import Celery

from blueberry_microid.infrastructure.config.settings import Settings, get_settings

ANALYSIS_QUEUE = "analysis"


def create_celery_app(settings: Settings | None = None) -> Celery:
    """Create the Celery application from environment-driven Settings."""
    resolved = settings or get_settings()
    app = Celery(
        "blueberry_microid",
        broker=resolved.celery_broker_url,
        backend=resolved.celery_result_backend,
        include=["blueberry_microid.infrastructure.tasks.analysis_tasks"],
    )
    app.conf.update(
        task_default_queue=ANALYSIS_QUEUE,
        task_routes={
            "blueberry_microid.infrastructure.tasks.analysis_tasks.process_analysis_run_task": {
                "queue": ANALYSIS_QUEUE
            }
        },
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_always_eager=resolved.celery_task_always_eager,
        task_eager_propagates=resolved.celery_task_eager_propagates,
        task_time_limit=resolved.celery_task_time_limit,
        task_soft_time_limit=resolved.celery_task_soft_time_limit,
    )
    return app


celery_app = create_celery_app()
