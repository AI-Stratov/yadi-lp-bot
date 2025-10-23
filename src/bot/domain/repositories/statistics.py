from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime


class StatisticsRepositoryInterface(ABC):
    @abstractmethod
    async def get_queue_len(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_scheduled_total(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_disk_group_counts(self) -> tuple[dict[str, int], int, Optional[datetime]]:
        """Возвращает (groups, common, computed_at) по кэшу лонг-поллера. Если кэша нет - ( {}, 0, None )."""
        raise NotImplementedError

