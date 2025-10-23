from abc import ABC, abstractmethod

from bot.domain.entities.statistics import StatsSnapshot


class StatisticsServiceInterface(ABC):
    @abstractmethod
    async def build_snapshot(self) -> StatsSnapshot:
        """Собрать агрегированную статистику для /stats."""
        raise NotImplementedError

