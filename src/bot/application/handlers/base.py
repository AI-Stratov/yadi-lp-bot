import bot.application.handlers.admin as admin
import bot.application.handlers.set as set
import bot.application.handlers.settings as settings
import bot.application.handlers.start as start
import bot.application.handlers.stats as stats
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from bot.domain.entities.mappings import UserType
from bot.domain.services.user import UserServiceInterface


def get_user_commands() -> list[BotCommand]:
    return [
        BotCommand(command="set", description="Настроить курс и группу"),
        BotCommand(command="settings", description="Настройки уведомлений"),
        BotCommand(command="help", description="Показать справку по командам"),
        BotCommand(command="cancel", description="Отменить текущую операцию"),
    ]


def get_admin_commands() -> list[BotCommand]:
    return [
        BotCommand(command="set", description="Настроить курс и группу"),
        BotCommand(command="settings", description="Настройки уведомлений"),
        BotCommand(command="stats", description="Статистика пользователей и очередей"),
        BotCommand(command="status", description="Статус сервисов и чекпоинт"),
        BotCommand(command="help", description="Показать справку по командам"),
        BotCommand(command="cancel", description="Отменить текущую операцию"),
    ]


def get_superuser_commands() -> list[BotCommand]:
    cmds = get_admin_commands()
    # раньше была команда "admins" — теперь "roles"
    cmds.insert(0, BotCommand(command="roles", description="Управление ролями"))
    return cmds


async def set_bot_commands(bot: Bot, user_service: UserServiceInterface):
    """Устанавливает разные команды бота в меню для администраторов и обычных пользователей"""
    # Базовые команды по умолчанию
    await bot.set_my_commands(get_user_commands(), scope=BotCommandScopeDefault())

    # Выставляем команды для админов и суперпользователей в их чатах
    admins = await user_service.get_users_by_type(UserType.ADMIN)
    supers = await user_service.get_users_by_type(UserType.SUPERUSER)

    for admin_user in admins:
        await bot.set_my_commands(get_admin_commands(), scope=BotCommandScopeChat(chat_id=admin_user.tg_id))

    for super_user in supers:
        await bot.set_my_commands(get_superuser_commands(), scope=BotCommandScopeChat(chat_id=super_user.tg_id))


def setup_handlers(dp: Dispatcher):
    setup_base(dp)


def setup_base(dp: Dispatcher):
    dp.include_router(start.router)
    dp.include_router(set.router)
    dp.include_router(settings.router)
    dp.include_router(stats.router)
    dp.include_router(admin.router)
