from abc import ABC, abstractmethod

from bot.domain.entities.mappings import UserType
from bot.domain.entities.user import CreateUserEntity, UpdateUserEntity
from bot.domain.entities.user import UserEntity


class UserServiceInterface(ABC):
    """Интерфейс сервиса управления пользователями"""

    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> UserEntity | None:
        """
        Получить пользователя по ID

        :param user_id: Telegram ID пользователя
        :return: данные пользователя или None
        """
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, user_data: CreateUserEntity) -> UserEntity:
        """
        Создать нового пользователя

        :param user_data: данные для создания пользователя
        :return: созданный пользователь
        """
        raise NotImplementedError

    @abstractmethod
    async def get_or_create(self, user_data: CreateUserEntity) -> UserEntity:
        """
        Получить существующего пользователя или создать нового

        :param user_data: данные пользователя
        :return: пользователь
        """
        raise NotImplementedError

    @abstractmethod
    async def update_user(self, user_id: int, user_data: UpdateUserEntity) -> UserEntity:
        """
        Обновить данные пользователя

        :param user_id: Telegram ID пользователя
        :param user_data: данные для обновления
        :return: обновленный пользователь
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_user(self, user_id: int) -> None:
        """
        Удалить пользователя

        :param user_id: Telegram ID пользователя
        """
        raise NotImplementedError

    @abstractmethod
    async def list_all_users(self) -> list[UserEntity]:
        """
        Получить список всех пользователей

        :return: список всех пользователей
        """
        raise NotImplementedError

    @abstractmethod
    async def get_users_by_type(self, user_type: UserType) -> list[UserEntity]:
        """
        Получить список пользователей по типу роли

        :param user_type: тип роли пользователя
        :return: список пользователей с указанной ролью
        """
        raise NotImplementedError

    @abstractmethod
    async def set_user_type(self, user_id: int, user_type: UserType) -> UserEntity:
        """
        Установить роль пользователя

        :param user_id: Telegram ID пользователя
        :param user_type: новая роль
        :return: обновленный пользователь
        """
        raise NotImplementedError
