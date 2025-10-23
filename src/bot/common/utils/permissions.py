"""Утилиты проверки прав доступа пользователей."""
from bot.domain.entities.mappings import UserType
from bot.domain.entities.user import UserEntity


def is_admin(user: UserEntity) -> bool:
    """
    Проверка наличия у пользователя прав администратора или суперпользователя

    :param user: сущность пользователя для проверки
    :return: True если пользователь ADMIN или SUPERUSER, иначе False
    """
    return getattr(user, "user_type", None) in (UserType.ADMIN, UserType.SUPERUSER)


def is_superuser(user: UserEntity) -> bool:
    """
    Проверка наличия у пользователя прав суперпользователя

    :param user: сущность пользователя для проверки
    :return: True если пользователь SUPERUSER, иначе False
    """
    return getattr(user, "user_type", None) == UserType.SUPERUSER
