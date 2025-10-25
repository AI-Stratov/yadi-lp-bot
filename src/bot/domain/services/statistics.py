from abc import ABC, abstractmethod

from bot.domain.entities.statistics import StatsSnapshot
from bot.domain.repositories.statistics import StatisticsRepositoryInterface
from bot.domain.services.user import UserServiceInterface


class StatisticsServiceInterface(ABC):
    def __init__(
        self,
        user_service: UserServiceInterface,
        repo: StatisticsRepositoryInterface,
    ):
        """
        Инициализация сервиса статистики

        :param user_service: сервис пользователей
        :param repo: репозиторий статистики
        """
        self.user_service = user_service
        self.repo = repo

    @abstractmethod
    async def build_snapshot(self) -> StatsSnapshot:
        """Собрать агрегированную статистику для /stats."""
        raise NotImplementedError
