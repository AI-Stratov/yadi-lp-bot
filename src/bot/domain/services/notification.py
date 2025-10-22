from abc import ABC, abstractmethod

from bot.domain.entities.notification import NotificationTask


class NotificationServiceInterface(ABC):
    @abstractmethod
    async def enqueue(self, task: NotificationTask) -> None:
        """Поставить одну задачу на рассылку."""
        raise NotImplementedError

    @abstractmethod
    async def enqueue_many(self, tasks: list[NotificationTask]) -> int:
        """Поставить несколько задач; вернуть количество поставленных."""
        raise NotImplementedError
