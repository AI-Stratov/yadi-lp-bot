from bot.domain.entities.user import UpdateUserEntity, CreateUserEntity, UserEntity
from bot.domain.repositories.user import UserRepositoryInterface
from bot.domain.services.user import UserServiceInterface


class UserService(UserServiceInterface):
    def __init__(
        self,
        user_repository: UserRepositoryInterface
    ):
        self.user_repository = user_repository

    async def get_user_by_id(self, user_id: int) -> UserEntity | None:
        return await self.user_repository.get_by_id(user_id)

    async def create_user(self, user_data: CreateUserEntity) -> UserEntity:
        return await self.user_repository.create(user_data)

    async def get_or_create(self, user_data: CreateUserEntity) -> UserEntity:
        return await self.user_repository.get_or_create(user_data)

    async def update_user(self, user_id: int, user_data: UpdateUserEntity) -> UserEntity:
        return await self.user_repository.update(user_id, user_data)

    async def delete_user(self, user_id: int) -> None:
        await self.user_repository.delete(user_id)

    async def list_all_users(self) -> list[UserEntity]:
        return await self.user_repository.list_all()
