import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("blueberry_microid.access")

_MAX_REQUEST_ID_LENGTH = 200


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Assigns a request_id to every request and logs one structured line per
    request (method, path, status_code, duration_ms).

    The request_id is stored on `request.state.request_id`, which
    `interfaces.api.error_handlers` reads to stamp the `X-Request-ID`
    response header — including on the "truly unexpected exception" path,
    where the response is actually built by Starlette's outer
    ServerErrorMiddleware, a layer that sits *outside* this middleware and
    that this middleware therefore never gets a `Response` object for (see
    ARCHITECTURE.md, "Fase 3.5"). Detailed error logging (with the
    traceback) also happens in `error_handlers.py`, not here, so a failing
    request is never logged twice.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_id = request.headers.get("x-request-id")
        request_id = incoming_id[:_MAX_REQUEST_ID_LENGTH] if incoming_id else uuid.uuid4().hex
        request.state.request_id = request_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        level = logging.ERROR if response.status_code >= 500 else logging.INFO
        logger.log(
            level,
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
