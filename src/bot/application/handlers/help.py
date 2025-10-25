from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.common.utils.permissions import is_admin, is_superuser
from bot.domain.entities.user import CreateUserEntity
from bot.domain.services.user import UserServiceInterface
from dishka import FromDishka
from dishka.integrations.aiogram import inject

router = Router(name="help")


@router.message(Command("help"))
@inject
async def cmd_help(
    message: types.Message,
    user_service: FromDishka[UserServiceInterface],
):
    """Показать справку по доступным командам с учётом роли пользователя."""
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(message.from_user))

    lines: list[str] = [
        "❓ <b>Справка по командам</b>",
        "",
        "Доступно всем:",
        "  • /set — настроить курс и группу",
        "  • /settings — настройки уведомлений (режим, время, исключения предметов)",
        "  • /help — показать эту справку",
        "  • /cancel — отменить текущую операцию (если запущен мастер)",
    ]

    if is_admin(caller):
        lines += [
            "",
            "Для администраторов:",
            "  • /stats — общая статистика сервиса",
            "  • /status — статус сервисов (long‑poll, планировщик, очереди)",
        ]

    if is_superuser(caller):
        lines += [
            "",
            "Для суперпользователя:",
            "  • /roles — управление ролями пользователей",
        ]

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отменить текущую операцию: очищает состояние FSM и уведомляет пользователя."""
    await state.clear()
    await message.answer("❎ Отменено")
