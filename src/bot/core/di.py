from collections.abc import AsyncIterator

import aiohttp
from aiogram import Bot
from dishka import AsyncContainer, Provider, Scope, provide
from dishka import make_async_container
from redis.asyncio import ConnectionPool, Redis

from bot.application.services.long_poll import YandexDiskPollingService
from bot.application.services.notification import RedisNotificationService
from bot.application.services.user import UserService
from bot.core.config import BotConfig, RedisConfig, YandexDiskConfig, bot_config, redis_config, yadisk_config
from bot.domain.repositories.user import UserRepositoryInterface
from bot.domain.services.notification import NotificationServiceInterface
from bot.domain.services.user import UserServiceInterface
from bot.infrastructure.repositories.user import RedisUserRepository


class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def get_bot_config(self) -> BotConfig:
        return bot_config

    @provide(scope=Scope.APP)
    def get_redis_config(self) -> RedisConfig:
        return redis_config

    @provide(scope=Scope.APP)
    def get_yadisk_config(self) -> YandexDiskConfig:
        return yadisk_config


class InfrastructureProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_redis_pool(self, config: RedisConfig) -> AsyncIterator[ConnectionPool]:
        pool = ConnectionPool(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD if config.REDIS_PASSWORD else None,
        )

        redis = Redis(connection_pool=pool)
        try:
            await redis.ping()
            print(f"✅ Подключено к Redis: {config.REDIS_HOST}:{config.REDIS_PORT}")
        finally:
            await redis.aclose()

        yield pool

        await pool.aclose()

    @provide(scope=Scope.APP)
    async def get_redis(self, pool: ConnectionPool) -> AsyncIterator[Redis]:
        redis = Redis(connection_pool=pool)
        yield redis
        await redis.aclose()

    @provide(scope=Scope.APP)
    async def get_http_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        async with aiohttp.ClientSession() as session:
            yield session

    @provide(scope=Scope.APP)
    def get_bot(self, config: BotConfig) -> Bot:
        return Bot(token=config.TOKEN.get_secret_value())


class RepositoryProvider(Provider):
    @provide(scope=Scope.APP)
    def get_user_repository(self, redis: Redis) -> UserRepositoryInterface:
        return RedisUserRepository(redis)


class ServiceProvider(Provider):
    @provide(scope=Scope.APP)
    def get_user_service(
        self,
        user_repository: UserRepositoryInterface,
    ) -> UserServiceInterface:
        return UserService(user_repository)

    @provide(scope=Scope.APP)
    def get_notification_service(self, redis: Redis) -> NotificationServiceInterface:
        return RedisNotificationService(redis)

    @provide(scope=Scope.APP)
    def get_polling_service(
        self,
        bot: Bot,
        user_service: UserServiceInterface,
        notification_service: NotificationServiceInterface,
        config: YandexDiskConfig,
        http_session: aiohttp.ClientSession,
        redis: Redis,
    ) -> YandexDiskPollingService:
        return YandexDiskPollingService(
            bot=bot,
            user_service=user_service,
            notification_service=notification_service,
            http=http_session,
            redis=redis,
            public_root_url=config.PUBLIC_ROOT_URL,
            poll_interval=config.POLL_INTERVAL,
            http_timeout=config.HTTP_TIMEOUT,
        )


async def create_container() -> AsyncContainer:
    container = make_async_container(
        ConfigProvider(),
        InfrastructureProvider(),
        RepositoryProvider(),
        ServiceProvider(),
    )

    return container
