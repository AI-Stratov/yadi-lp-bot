from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterator

from bot.domain.entities.notification import NotificationTask, UserNotification


class NotificationRepositoryInterface(ABC):
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
