from abc import ABC, abstractmethod

import aiohttp
from aiogram import Bot
from redis.asyncio import Redis

from bot.domain.services.notification import NotificationServiceInterface
from bot.domain.services.user import UserServiceInterface


class LongPollServiceInterface(ABC):
    def __init__(
        self,
        bot: Bot,
        user_service: UserServiceInterface,
        notification_service: NotificationServiceInterface,
        http: aiohttp.ClientSession,
        redis: Redis,
        public_root_url: str,
        poll_interval: int,
        http_timeout: float,
        key_prefix: str = "",
    ):
        self.bot = bot
        self.user_service = user_service
        self.notification_service = notification_service
        self.http = http
        self.redis = redis
        self.public_root_url = public_root_url
        self.poll_interval = poll_interval
        self.http_timeout = http_timeout
        self.key_prefix = key_prefix.strip().rstrip(":") if key_prefix else ""
        self._running = False

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass
