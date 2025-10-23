"""
Интерфейс сервиса планировщика уведомлений.

Предоставляет единый контракт для реализаций планировщика
"""

from abc import ABC, abstractmethod


class SchedulerServiceInterface(ABC):
    """
    Планировщик доставки уведомлений по расписанию.

    """

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
