from typing import Any

from pydantic import BaseModel


class TaskStatusRead(BaseModel):
    task_id: str
    state: str
    result: dict[str, Any] | None
