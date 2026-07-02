from celery import Celery
from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from blueberry_microid.interfaces.api.v1.dependencies import get_celery_app
from blueberry_microid.interfaces.api.v1.schemas.task import TaskStatusRead

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskStatusRead)
def get_task_status(task_id: str, app: Celery = Depends(get_celery_app)) -> TaskStatusRead:
    result = AsyncResult(task_id, app=app)
    if result.failed():
        payload = {"message": "Task failed"}
    elif result.successful() and isinstance(result.result, dict):
        payload = result.result
    elif result.ready():
        payload = {"message": "Task finished"}
    else:
        payload = {}

    return TaskStatusRead(task_id=task_id, state=result.state, result=payload)
