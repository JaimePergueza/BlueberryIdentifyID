from blueberry_microid.application.dto.auth_dto import UserDTO
from blueberry_microid.application.ports.password_hasher import PasswordHasherPort
from blueberry_microid.application.ports.user_repository import UserRepositoryPort
from blueberry_microid.domain.entities.user import User
from blueberry_microid.domain.enums.user_role import UserRole


class CreateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        password_hasher: PasswordHasherPort,
    ) -> None:
        self._users = user_repository
        self._password_hasher = password_hasher

    def execute(self, username: str, password: str, role: UserRole) -> UserDTO:
        user = User(
            username=username,
            password_hash=self._password_hasher.hash(password),
            role=role,
        )
        return UserDTO.from_entity(self._users.add(user))
