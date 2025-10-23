from datetime import datetime

from bot.domain.entities.user import UserEntity, UpdateUserEntity, CreateUserEntity
from bot.domain.repositories.user import UserRepositoryInterface


class RedisUserRepository(UserRepositoryInterface):
    """Реализация репозитория пользователей на основе Redis"""
    PREFIX = 'users'

    @staticmethod
    def _to_str(v):
        """Преобразовать байты в строку"""
        return v.decode() if isinstance(v, (bytes, bytearray)) else v

    def _key(self, base: str) -> str:
        """Получить полный ключ с префиксом"""
        return f'{self._prefix}:{base}' if self._prefix else base

    def _get_key(self, tg_id: int) -> str:
        """Получить ключ для пользователя"""
        return self._key(f'{self.PREFIX}:{tg_id}')

    async def get_by_id(self, tg_id: int) -> UserEntity | None:
        """Получить пользователя по ID"""
        raw = await self.redis.get(self._get_key(tg_id))
        if not raw:
            return None
        return UserEntity.model_validate_json(self._to_str(raw))

    async def create(self, create_user_e: CreateUserEntity) -> UserEntity:
        """Создать нового пользователя"""
        entity = UserEntity(**create_user_e.model_dump())
        await self.redis.set(self._get_key(entity.tg_id), entity.model_dump_json())
        return entity

    async def get_or_create(self, user: CreateUserEntity) -> UserEntity:
        """Получить существующего пользователя или создать нового"""
        existing = await self.get_by_id(user.tg_id)
        return existing or await self.create(user)

    async def update(self, tg_id: int, update_user_e: UpdateUserEntity) -> UserEntity:
        """Обновить данные пользователя"""
        existing = await self.get_by_id(tg_id)
        if not existing:
            raise ValueError('User not found')
        data = existing.model_dump()
        data.update(update_user_e.model_dump(exclude_unset=True))
        data['updated_at'] = datetime.now()
        entity = UserEntity(**data)
        await self.redis.set(self._get_key(tg_id), entity.model_dump_json())
        return entity

    async def delete(self, tg_id: int) -> bool:
        """Удалить пользователя"""
        return bool(await self.redis.delete(self._get_key(tg_id)))

    async def list_all(self) -> list[UserEntity]:
        """Получить список всех пользователей"""
        pattern = self._key(f'{self.PREFIX}:*')
        users: list[UserEntity] = []
        async for key in self.redis.scan_iter(match=pattern):
            k = self._to_str(key)
            t = self._to_str(await self.redis.type(k))
            if t != 'string':
                continue
            raw = await self.redis.get(k)
            if not raw:
                continue
            try:
                users.append(UserEntity.model_validate_json(self._to_str(raw)))
            except Exception:
                continue
        return users
