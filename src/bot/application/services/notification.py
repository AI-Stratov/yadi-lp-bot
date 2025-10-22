from typing import Iterable

from redis.asyncio import Redis

from bot.domain.entities.notification import NotificationTask
from bot.domain.services.notification import NotificationServiceInterface


class RedisNotificationService(NotificationServiceInterface):
    def __init__(self, redis: Redis, queue_key: str = "yadi-lp:notify_queue"):
        self.redis = redis
        self.queue_key = queue_key

    async def enqueue(self, task: NotificationTask) -> None:
        await self.redis.rpush(self.queue_key, task.model_dump_json())

    async def enqueue_many(self, tasks: list[NotificationTask]) -> int:
        if not tasks:
            return 0
        payloads: Iterable[str] = (t.model_dump_json() for t in tasks)
        await self.redis.rpush(self.queue_key, *payloads)
        return len(tasks)

