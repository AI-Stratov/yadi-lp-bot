"""Утилиты для сортировки пользователей.

Предназначены для переиспользования в хендлерах и сервисах.
"""

from bot.domain.entities.user import UserEntity


def sort_users(users: list[UserEntity]) -> list[UserEntity]:
    """
    Отсортировать пользователей по display_name (без учёта регистра) и tg_id.

    :param users: список пользователей
    :return: отсортированный список
    """
    return sorted(users, key=lambda u: (u.display_name.lower(), u.tg_id))
