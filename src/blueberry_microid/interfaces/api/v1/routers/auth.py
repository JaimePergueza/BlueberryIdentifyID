from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from blueberry_microid.application.dto.auth_dto import UserDTO
from blueberry_microid.application.use_cases.auth.login import LoginUseCase
from blueberry_microid.application.use_cases.auth.logout import LogoutUseCase
from blueberry_microid.domain.entities.user import User
from blueberry_microid.interfaces.api.security import (
    get_current_raw_token,
    get_current_user,
    get_login_use_case,
    get_logout_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.auth import LoginRead, LogoutRead, UserRead

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginRead, status_code=status.HTTP_200_OK)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> LoginRead:
    """Authenticate an active user and issue a revocable opaque bearer token."""
    return LoginRead.model_validate(use_case.execute(form_data.username, form_data.password))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(UserDTO.from_entity(current_user))


@router.post("/logout", response_model=LogoutRead)
def logout(
    raw_token: str = Depends(get_current_raw_token),
    _current_user: User = Depends(get_current_user),
    use_case: LogoutUseCase = Depends(get_logout_use_case),
) -> LogoutRead:
    use_case.execute(raw_token)
    return LogoutRead(message="Session revoked")
