from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterator

from bot.domain.entities.notification import NotificationTask, UserNotification


class NotificationRepositoryInterface(ABC):
    BASE_QUEUE = 'notifications:queue'
    BASE_USER = 'notifications:user:{user_id}'
    BASE_SENT = 'notifications:sent:{user_id}'
    BASE_STATUS = 'notifications:status:{notification_id}'

    def __init__(self, redis, key_prefix: str = ''):
        self.redis = redis
        self._prefix = key_prefix.strip().rstrip(':') if key_prefix else ''

    @abstractmethod
    async def push_to_queue(self, tasks: list[NotificationTask]) -> None:
        """Добавляет задачи в общую очередь для обработки"""
        raise NotImplementedError

    @abstractmethod
    async def pop_from_queue(self, batch_size: int = 100) -> AsyncIterator[NotificationTask]:
        """Извлекает задачи из общей очереди"""
        raise NotImplementedError

    @abstractmethod
    async def save_user_notification(self, notification: UserNotification) -> None:
        """Сохраняет персональное уведомление пользователя"""
        raise NotImplementedError

    @abstractmethod
    async def get_due_notifications(self, before: datetime, limit: int = 100) -> AsyncIterator[UserNotification]:
        """Получает уведомления, которые нужно отправить до указанного времени"""
        raise NotImplementedError

    @abstractmethod
    async def mark_as_sent(self, notification_id: str) -> None:
        """Помечает уведомление как отправленное"""
        raise NotImplementedError

    @abstractmethod
    async def mark_as_failed(self, notification_id: str, error: str) -> None:
        """Помечает уведомление как неудачное"""
        raise NotImplementedError

    @abstractmethod
    async def is_duplicate(self, user_id: int, task: NotificationTask) -> bool:
        """Проверяет, было ли уже отправлено уведомление о таком файле пользователю"""
        raise NotImplementedError
