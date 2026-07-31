from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from blueberry_microid.application.auth_exceptions import (
    AuthenticationRequiredError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    LastActiveAdminError,
    PermissionDeniedError,
    UserNotFoundError,
)


def _response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    payload = {"error": {"code": code, "message": message}}
    request_id = getattr(request.state, "request_id", None)
    if request_id is not None:
        payload["error"]["request_id"] = request_id
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


async def _invalid_credentials(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
    return _response(request, 401, "invalid_credentials", "Invalid username or password")


async def _authentication_required(
    request: Request, exc: AuthenticationRequiredError
) -> JSONResponse:
    return _response(request, 401, "authentication_required", "A valid bearer session is required")


async def _permission_denied(request: Request, exc: PermissionDeniedError) -> JSONResponse:
    return _response(request, 403, "permission_denied", str(exc))


async def _user_not_found(request: Request, exc: UserNotFoundError) -> JSONResponse:
    return _response(request, 404, "user_not_found", str(exc))


async def _duplicate_username(request: Request, exc: DuplicateUsernameError) -> JSONResponse:
    return _response(request, 409, "duplicate_username", str(exc))


async def _last_admin(request: Request, exc: LastActiveAdminError) -> JSONResponse:
    return _response(request, 409, "last_active_admin", str(exc))


def register_auth_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InvalidCredentialsError, _invalid_credentials)
    app.add_exception_handler(AuthenticationRequiredError, _authentication_required)
    app.add_exception_handler(PermissionDeniedError, _permission_denied)
    app.add_exception_handler(UserNotFoundError, _user_not_found)
    app.add_exception_handler(DuplicateUsernameError, _duplicate_username)
    app.add_exception_handler(LastActiveAdminError, _last_admin)
