from bot.domain.entities.user import UpdateUserEntity, CreateUserEntity, UserEntity
from bot.domain.repositories.user import UserRepositoryInterface
from bot.domain.services.user import UserServiceInterface
from bot.domain.entities.mappings import UserType
from bot.core.config import BotConfig


class UserService(UserServiceInterface):
    def __init__(
        self,
        user_repository: UserRepositoryInterface,
        bot_config: BotConfig | None = None,
    ):
        self.user_repository = user_repository
        self._superuser_id = bot_config.SUPERUSER_ID if bot_config else None

    async def get_user_by_id(self, user_id: int) -> UserEntity | None:
        return await self.user_repository.get_by_id(user_id)

    async def create_user(self, user_data: CreateUserEntity) -> UserEntity:
        user = await self.user_repository.create(user_data)
        return await self._maybe_apply_superuser(user)

    async def get_or_create(self, user_data: CreateUserEntity) -> UserEntity:
        user = await self.user_repository.get_or_create(user_data)
        return await self._maybe_apply_superuser(user)

    async def update_user(self, user_id: int, user_data: UpdateUserEntity) -> UserEntity:
        user = await self.user_repository.update(user_id, user_data)
        return user

    async def delete_user(self, user_id: int) -> None:
        await self.user_repository.delete(user_id)

    async def list_all_users(self) -> list[UserEntity]:
        return await self.user_repository.list_all()

    async def get_users_by_type(self, user_type: UserType) -> list[UserEntity]:
        users = await self.user_repository.list_all()
        return [u for u in users if u.user_type == user_type]

    async def set_user_type(self, user_id: int, user_type: UserType) -> UserEntity:
        return await self.user_repository.update(user_id, UpdateUserEntity(user_type=user_type))

    async def _maybe_apply_superuser(self, user: UserEntity) -> UserEntity:
        if self._superuser_id and user.tg_id == self._superuser_id and user.user_type != UserType.SUPERUSER:
            return await self.user_repository.update(user.tg_id, UpdateUserEntity(user_type=UserType.SUPERUSER))
        return user
