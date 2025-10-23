import json
import uuid
from datetime import datetime
from typing import AsyncIterator

from bot.domain.entities.notification import NotificationTask, UserNotification
from bot.domain.repositories.notification import NotificationRepositoryInterface


class RedisNotificationRepository(NotificationRepositoryInterface):
    BASE_QUEUE = 'notifications:queue'
    BASE_USER = 'notifications:user:{user_id}'
    BASE_SENT = 'notifications:sent:{user_id}'
    BASE_STATUS = 'notifications:status:{notification_id}'

    def __init__(self, redis, key_prefix: str = ''):
        self.redis = redis
        self._prefix = key_prefix.strip().rstrip(':') if key_prefix else ''

    def _to_str(self, v):
        return v.decode() if isinstance(v, (bytes, bytearray)) else v

    def _key(self, base: str) -> str:
        return f'{self._prefix}:{base}' if self._prefix else base

    def _queue_key(self) -> str:
        return self._key(self.BASE_QUEUE)

    def _user_key(self, user_id: int) -> str:
        return self._key(self.BASE_USER.format(user_id=user_id))

    def _sent_key(self, user_id: int) -> str:
        return self._key(self.BASE_SENT.format(user_id=user_id))

    def _status_key(self, notification_id: str) -> str:
        return self._key(self.BASE_STATUS.format(notification_id=notification_id))

    async def push_to_queue(self, tasks: list[NotificationTask]) -> None:
        if not tasks:
            return
        pipeline = self.redis.pipeline()
        q = self._queue_key()
        for task in tasks:
            pipeline.rpush(q, task.model_dump_json())
        await pipeline.execute()

    async def pop_from_queue(self, batch_size: int = 100) -> AsyncIterator[NotificationTask]:
        q = self._queue_key()
        for _ in range(batch_size):
            raw = await self.redis.lpop(q)
            if not raw:
                break
            data = json.loads(self._to_str(raw))
            yield NotificationTask.model_validate(data)

    async def save_user_notification(self, notification: UserNotification) -> None:
        if not notification.notification_id:
            notification.notification_id = str(uuid.uuid4())
        key = self._user_key(notification.user_id)
        score = notification.scheduled_at.timestamp() if notification.scheduled_at else datetime.now().timestamp()
        await self.redis.zadd(key, {notification.model_dump_json(): score})

    async def get_due_notifications(self, before: datetime, limit: int = 100) -> AsyncIterator[UserNotification]:
        cursor = 0
        pattern = self._key('notifications:user:*')
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                k = self._to_str(key)
                members = await self.redis.zrangebyscore(k, min=0, max=before.timestamp(), start=0, num=limit)
                for m in members:
                    n = UserNotification.model_validate(json.loads(self._to_str(m)))
                    await self.redis.zrem(k, m)
                    yield n
            if cursor == 0:
                break

    async def mark_as_sent(self, notification_id: str) -> None:
        key = self._status_key(notification_id)
        await self.redis.hset(key, mapping={'status': 'sent', 'sent_at': datetime.now().isoformat()})
        await self.redis.expire(key, 86400 * 7)

    async def mark_as_failed(self, notification_id: str, error: str) -> None:
        key = self._status_key(notification_id)
        await self.redis.hset(key, mapping={'status': 'failed', 'error': error, 'failed_at': datetime.now().isoformat()})
        await self.redis.expire(key, 86400 * 7)

    async def is_duplicate(self, user_id: int, task: NotificationTask) -> bool:
        key = self._sent_key(user_id)
        file_id = task.md5 or task.resource_id or f'{task.file_path}:{task.modified_iso}'
        exists = await self.redis.sismember(key, file_id)
        if not exists:
            await self.redis.sadd(key, file_id)
            await self.redis.expire(key, 86400 * 30)
        return bool(exists)
