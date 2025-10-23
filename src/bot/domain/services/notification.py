from abc import ABC, abstractmethod

from bot.domain.entities.notification import NotificationTask


class NotificationServiceInterface(ABC):
    @abstractmethod
    async def enqueue_many(self, tasks: list[NotificationTask]) -> None:
        """Добавляет задачи в общую очередь для обработки"""
        raise NotImplementedError

    @abstractmethod
    async def process_queue(self) -> int:
        """Обрабатывает очередь: распределяет уведомления по пользователям с учетом их настроек"""
        raise NotImplementedError
