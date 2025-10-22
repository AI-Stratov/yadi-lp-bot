from abc import ABC, abstractmethod

from bot.domain.entities.user import UserEntity
from bot.domain.entities.user import CreateUserEntity, UpdateUserEntity


class UserServiceInterface(ABC):
    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> UserEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, user_data: CreateUserEntity) -> UserEntity:
        raise NotImplementedError

    @abstractmethod
    async def get_or_create(self, user_data: CreateUserEntity) -> UserEntity:
        raise NotImplementedError

    @abstractmethod
    async def update_user(self, user_id: int, user_data: UpdateUserEntity) -> UserEntity:
        raise NotImplementedError

    @abstractmethod
    async def delete_user(self, user_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_all_users(self) -> list[UserEntity]:
        raise NotImplementedError
