from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.use_cases.auth.create_user import CreateUserUseCase
from blueberry_microid.application.use_cases.auth.list_users import ListUsersUseCase
from blueberry_microid.application.use_cases.auth.update_user import UpdateUserUseCase
from blueberry_microid.interfaces.api.security import (
    get_create_user_use_case,
    get_list_users_use_case,
    get_update_user_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.auth import (
    UserCreate,
    UserListRead,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
) -> UserRead:
    return UserRead.model_validate(
        use_case.execute(payload.username, payload.password, payload.role)
    )


@router.get("", response_model=UserListRead)
def list_users(
    use_case: ListUsersUseCase = Depends(get_list_users_use_case),
) -> UserListRead:
    return UserListRead(users=[UserRead.model_validate(user) for user in use_case.execute()])


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    use_case: UpdateUserUseCase = Depends(get_update_user_use_case),
) -> UserRead:
    return UserRead.model_validate(
        use_case.execute(
            user_id,
            role=payload.role,
            is_active=payload.is_active,
            password=payload.password,
        )
    )
