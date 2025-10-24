"""
Интерфейс сервиса планировщика уведомлений.

Предоставляет единый контракт для реализаций планировщика
"""

from abc import ABC, abstractmethod

from aiogram import Bot

from bot.domain.repositories.notification import NotificationRepositoryInterface


class SchedulerServiceInterface(ABC):
    """
    Планировщик доставки уведомлений по расписанию.

    """

    def __init__(
        self,
        bot: Bot,
        repository: NotificationRepositoryInterface,
        check_interval: int = 60,
    ):
        self.bot = bot
        self.repository = repository
        self._check_interval = check_interval
        self._running = False
        self._task = None

    @property
    @abstractmethod
    def check_interval(self) -> int:
        """
        Периодичность проверки очереди (в секундах).

        :return: интервал в секундах
        """

    @abstractmethod
    async def start(self) -> None:
        """
        Запустить планировщик.

        :return: None
        """

    @abstractmethod
    async def stop(self) -> None:
        """
        Остановить планировщик и дождаться завершения фоновой задачи.

        :return: None
        """
