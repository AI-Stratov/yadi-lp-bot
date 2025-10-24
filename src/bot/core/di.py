from collections.abc import AsyncIterator

import aiohttp
from aiogram import Bot
from dishka import AsyncContainer, Provider, Scope, provide
from dishka import make_async_container
from redis.asyncio import ConnectionPool, Redis

from bot.application.services.long_poll import YandexDiskPollingService
from bot.application.services.notification import NotificationService
from bot.application.services.scheduler import NotificationScheduler
from bot.application.services.statistics import StatisticsService
from bot.application.services.user import UserService
from bot.application.widgets.time_picker import TimePicker
from bot.core.config import BotConfig, RedisConfig, YandexDiskConfig, NotificationsConfig
from bot.domain.entities.constants import DEFAULT_MINUTE_STEP
from bot.domain.repositories.notification import NotificationRepositoryInterface
from bot.domain.repositories.statistics import StatisticsRepositoryInterface
from bot.domain.repositories.user import UserRepositoryInterface
from bot.domain.services.notification import NotificationServiceInterface
from bot.domain.services.scheduler import SchedulerServiceInterface
from bot.domain.services.statistics import StatisticsServiceInterface
from bot.domain.services.user import UserServiceInterface
from bot.infrastructure.repositories.notification import RedisNotificationRepository
from bot.infrastructure.repositories.statistics import RedisStatisticsRepository
from bot.infrastructure.repositories.user import RedisUserRepository


class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def get_bot_config(self) -> BotConfig:
        return BotConfig()

    @provide(scope=Scope.APP)
    def get_redis_config(self) -> RedisConfig:
        return RedisConfig()

    @provide(scope=Scope.APP)
    def get_yadisk_config(self) -> YandexDiskConfig:
        return YandexDiskConfig()

    @provide(scope=Scope.APP)
    def get_notifications_config(self) -> NotificationsConfig:
        return NotificationsConfig()


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
    def get_user_repository(self, redis: Redis, config: RedisConfig) -> UserRepositoryInterface:
        return RedisUserRepository(redis, key_prefix=config.REDIS_KEY_PREFIX)

    @provide(scope=Scope.APP)
    def get_notification_repository(self, redis: Redis, config: RedisConfig) -> NotificationRepositoryInterface:
        return RedisNotificationRepository(redis, key_prefix=config.REDIS_KEY_PREFIX)

    @provide(scope=Scope.APP)
    def get_statistics_repository(self, redis: Redis, rconf: RedisConfig, yconf: YandexDiskConfig) -> StatisticsRepositoryInterface:
        return RedisStatisticsRepository(redis, key_prefix=rconf.REDIS_KEY_PREFIX, public_root_url=yconf.PUBLIC_ROOT_URL)


class ServiceProvider(Provider):
    @provide(scope=Scope.APP)
    def get_user_service(
        self,
        user_repository: UserRepositoryInterface,
        config: BotConfig,
    ) -> UserServiceInterface:
        return UserService(user_repository, config)

    @provide(scope=Scope.APP)
    def get_notification_service(
        self,
        notification_repository: NotificationRepositoryInterface,
        user_service: UserServiceInterface,
    ) -> NotificationServiceInterface:
        return NotificationService(notification_repository, user_service)

    @provide(scope=Scope.APP)
    def get_statistics_service(
        self,
        user_service: UserServiceInterface,
        repo: StatisticsRepositoryInterface,
    ) -> StatisticsServiceInterface:
        return StatisticsService(user_service, repo)

    @provide(scope=Scope.APP)
    def get_notification_scheduler(
        self,
        bot: Bot,
        notification_repository: NotificationRepositoryInterface,
        notifications_config: NotificationsConfig,
    ) -> SchedulerServiceInterface:
        return NotificationScheduler(bot, notification_repository, check_interval=notifications_config.NOTIFICATION_CHECK_INTERVAL)

    @provide(scope=Scope.APP)
    def get_polling_service(
        self,
        bot: Bot,
        user_service: UserServiceInterface,
        notification_service: NotificationServiceInterface,
        config: YandexDiskConfig,
        http_session: aiohttp.ClientSession,
        redis: Redis,
        redis_config: RedisConfig,
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
            key_prefix=redis_config.REDIS_KEY_PREFIX,
        )


class WidgetProvider(Provider):
    """Провайдер UI-виджетов"""

    @provide(scope=Scope.REQUEST)
    def get_time_picker(self) -> TimePicker:
        """
        Предоставляет экземпляр виджета TimePicker

        :return: настроенный TimePicker с дефолтными параметрами
        """

        return TimePicker(prefix="tp", minute_step=DEFAULT_MINUTE_STEP, show_cancel=True)


async def create_container() -> AsyncContainer:
    container = make_async_container(
        ConfigProvider(),
        InfrastructureProvider(),
        RepositoryProvider(),
        ServiceProvider(),
        WidgetProvider(),
    )

    return container
