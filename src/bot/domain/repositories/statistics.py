from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from redis.asyncio import Redis


class StatisticsRepositoryInterface(ABC):
    def __init__(self, redis: Redis, key_prefix: str, public_root_url: str):
        self.redis = redis
        self.key_prefix = key_prefix.strip().rstrip(":") if key_prefix else ""
        self.public_root_url = public_root_url

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
