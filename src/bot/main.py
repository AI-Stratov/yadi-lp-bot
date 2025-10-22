import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from dishka.integrations.aiogram import setup_dishka
from redis.asyncio import Redis

from bot.application.handlers.base import setup_handlers
from bot.application.services.long_poll import YandexDiskPollingService
from bot.common.logs import logger
from bot.core.di import create_container


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

        # Запускаем long-poll сервис
        polling_service = await container.get(YandexDiskPollingService)
        await polling_service.start()
        logger.info("✅ Long-polling сервис запущен")

        logger.info("✅ Бот готов к работе!")

        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        finally:
            # Останавливаем long-polling при завершении
            await polling_service.stop()
    finally:
        # Закрываем контейнер
        await container.close()
        logger.info("👋 Бот остановлен")


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал остановки. Завершаем работу бота...")


if __name__ == "__main__":
    run()
