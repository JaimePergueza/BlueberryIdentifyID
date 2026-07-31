from blueberry_microid.application.dto.auth_dto import UserDTO
from blueberry_microid.application.ports.user_repository import UserRepositoryPort


class ListUsersUseCase:
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._users = user_repository

    def execute(self) -> list[UserDTO]:
        return [UserDTO.from_entity(user) for user in self._users.list_all()]
