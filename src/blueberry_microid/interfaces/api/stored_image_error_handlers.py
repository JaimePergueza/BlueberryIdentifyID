from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from blueberry_microid.application.stored_image_exceptions import StoredImageUnavailableError


async def _stored_image_unavailable(
    request: Request,
    exc: StoredImageUnavailableError,
) -> JSONResponse:
    error: dict[str, str] = {
        "code": "stored_image_unavailable",
        "message": "Stored image content is unavailable",
    }
    request_id = getattr(request.state, "request_id", None)
    if request_id is not None:
        error["request_id"] = request_id
    return JSONResponse(status_code=404, content={"error": error})


def register_stored_image_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StoredImageUnavailableError, _stored_image_unavailable)
