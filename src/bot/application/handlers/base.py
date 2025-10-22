from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault

import bot.application.handlers.set as set
import bot.application.handlers.settings as settings
import bot.application.handlers.start as start


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="set", description="Настроить курс и группу"),
        BotCommand(command="settings", description="Настройки уведомлений"),
        BotCommand(command="help", description="Показать справку по командам"),
        BotCommand(command="cancel", description="Отменить текущую операцию"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


def setup_handlers(dp: Dispatcher):
    setup_base(dp)
    dp.startup.register(set_bot_commands)


def setup_base(dp: Dispatcher):
    dp.include_router(start.router)
    dp.include_router(set.router)
    dp.include_router(settings.router)
