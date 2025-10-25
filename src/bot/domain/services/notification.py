from abc import ABC, abstractmethod

from bot.domain.entities.notification import NotificationTask
from bot.domain.repositories.notification import NotificationRepositoryInterface
from bot.domain.services.user import UserServiceInterface


class NotificationServiceInterface(ABC):
    def __init__(
        self,
        notification_repository: NotificationRepositoryInterface,
        user_service: UserServiceInterface,
    ):
        self.repository = notification_repository
        self.user_service = user_service

    @abstractmethod
    async def enqueue_many(self, tasks: list[NotificationTask]) -> None:
        """Добавляет задачи в общую очередь для обработки"""
        raise NotImplementedError

    @abstractmethod
    async def process_queue(self) -> int:
        """Обрабатывает очередь: распределяет уведомления по пользователям с учетом их настроек"""
        raise NotImplementedError
