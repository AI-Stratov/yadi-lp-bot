import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from dishka.integrations.aiogram import setup_dishka
from redis.asyncio import Redis

from bot.application.handlers.base import setup_handlers, set_bot_commands
from bot.application.services.long_poll import YandexDiskPollingService
from bot.common.logs import logger
from bot.core.di import create_container
from bot.domain.services.notification import NotificationServiceInterface
from bot.domain.services.scheduler import SchedulerServiceInterface
from bot.domain.services.user import UserServiceInterface


async def main():
    logger.info("🚀 Запуск бота...")

    # Создаем DI контейнер
    container = await create_container()

    try:
        # Получаем зависимости из контейнера
        bot = await container.get(Bot)
        redis = await container.get(Redis)

        storage = RedisStorage(redis=redis)
        dp = Dispatcher(storage=storage)

        # Настраиваем dishka для автоматического внедрения зависимостей в handlers
        setup_dishka(container, dp)

        # Регистрируем обработчики
        setup_handlers(dp)
        logger.info("✅ Handlers зарегистрированы")

        # Устанавливаем команды бота (разные для админов/пользователей)
        user_service = await container.get(UserServiceInterface)
        await set_bot_commands(bot, user_service)
        logger.info("✅ Команды бота установлены")

        # Запускаем long-poll сервис
        polling_service = await container.get(YandexDiskPollingService)
        await polling_service.start()
        logger.info("✅ Long-polling сервис запущен")

        # Запускаем планировщик уведомлений (через интерфейс)
        scheduler = await container.get(SchedulerServiceInterface)
        await scheduler.start()
        logger.info("✅ Планировщик уведомлений запущен")

        # Запускаем фоновый процессор очереди уведомлений
        notification_service = await container.get(NotificationServiceInterface)
        queue_processor_task = asyncio.create_task(
            _process_notification_queue_loop(notification_service),
            name="notification_queue_processor"
        )
        logger.info("✅ Процессор очереди уведомлений запущен")

        logger.info("✅ Бот готов к работе!")

        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        finally:
            # Останавливаем все фоновые процессы
            queue_processor_task.cancel()
            try:
                await queue_processor_task
            except asyncio.CancelledError:
                pass

            await scheduler.stop()
            await polling_service.stop()
    finally:
        # Закрываем контейнер
        await container.close()
        logger.info("👋 Бот остановлен")


async def _process_notification_queue_loop(notification_service: NotificationServiceInterface):
    """Фоновая задача для обработки очереди уведомлений"""
    while True:
        try:
            processed = await notification_service.process_queue()
            if processed == 0:
                # Если очередь пуста, ждём дольше
                await asyncio.sleep(30)
            else:
                # Если были задачи, проверяем чаще
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("🛑 Процессор очереди уведомлений остановлен")
            raise
        except Exception as e:
            logger.exception(f"Ошибка в процессоре очереди уведомлений: {e}")
            await asyncio.sleep(10)


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал остановки. Завершаем работу бота...")


if __name__ == "__main__":
    run()
