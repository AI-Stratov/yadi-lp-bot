from datetime import datetime

from bot.domain.entities.user import UserEntity, UpdateUserEntity, CreateUserEntity
from bot.domain.repositories.user import UserRepositoryInterface


class RedisUserRepository(UserRepositoryInterface):
    def _get_key(self, tg_id: int) -> str:
        return f"{self.prefix}:{tg_id}"

    async def get_by_id(self, tg_id: int) -> UserEntity | None:
        data = await self.redis.get(self._get_key(tg_id))
        if not data:
            return None
        return UserEntity.model_validate_json(data)

    async def create(self, create_user_e: CreateUserEntity) -> UserEntity:
        entity = UserEntity(**create_user_e.model_dump())
        await self.redis.set(self._get_key(entity.tg_id), entity.model_dump_json())
        return entity

    async def get_or_create(self, user: CreateUserEntity) -> UserEntity:
        existing = await self.get_by_id(user.tg_id)
        if existing:
            return existing
        return await self.create(user)

    async def update(self, tg_id: int, update_user_e: UpdateUserEntity) -> UserEntity:
        existing = await self.get_by_id(tg_id)
        if not existing:
            raise ValueError("User not found")

        data = existing.model_dump()
        updates = update_user_e.model_dump(exclude_unset=True)
        data.update(updates)
        data["updated_at"] = datetime.now()

        entity = UserEntity(**data)
        await self.redis.set(self._get_key(tg_id), entity.model_dump_json())
        return entity

    async def delete(self, tg_id: int) -> bool:
        result = await self.redis.delete(self._get_key(tg_id))
        return bool(result)

    async def list_all(self) -> list[UserEntity]:
        pattern = f"{self.prefix}:*"
        users: list[UserEntity] = []
        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.get(key)
            if not data:
                continue
            try:
                users.append(UserEntity.model_validate_json(data))
            except Exception:
                continue
        return users
