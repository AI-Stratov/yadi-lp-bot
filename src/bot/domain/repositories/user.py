from abc import ABC, abstractmethod

from redis.asyncio import Redis

from bot.domain.entities.user import UserEntity, CreateUserEntity, UpdateUserEntity


class UserRepositoryInterface(ABC):
    def __init__(
        self,
        redis: Redis
    ):
        self.redis = redis
        self.prefix = "yadi-lp:user"

    @abstractmethod
    async def get_by_id(self, tg_id: int) -> UserEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, create_user_e: CreateUserEntity) -> UserEntity:
        raise NotImplementedError

    @abstractmethod
    async def get_or_create(self, user: CreateUserEntity) -> UserEntity:
        raise NotImplementedError

    @abstractmethod
    async def update(self, tg_id: int, update_user_e: UpdateUserEntity) -> UserEntity:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, tg_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[UserEntity]:
        """Вернуть всех пользователей из хранилища."""
        raise NotImplementedError
