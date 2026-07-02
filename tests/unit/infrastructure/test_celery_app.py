from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.tasks.celery_app import ANALYSIS_QUEUE, create_celery_app


def test_celery_app_uses_safe_json_configuration():
    app = create_celery_app(
        Settings(
            _env_file=None,
            celery_broker_url="redis://redis:6379/5",
            celery_result_backend="redis://redis:6379/6",
        )
    )

    assert app.conf.broker_url == "redis://redis:6379/5"
    assert app.conf.result_backend == "redis://redis:6379/6"
    assert app.conf.task_serializer == "json"
    assert app.conf.result_serializer == "json"
    assert app.conf.accept_content == ["json"]
    assert "pickle" not in app.conf.accept_content
    assert app.conf.task_default_queue == ANALYSIS_QUEUE
    assert app.conf.task_track_started is True
