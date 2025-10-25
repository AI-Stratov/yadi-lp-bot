from aiogram import Router, types
from aiogram.filters import CommandStart
from bot.domain.entities.user import CreateUserEntity
from bot.domain.services.user import UserServiceInterface
from dishka import FromDishka
from dishka.integrations.aiogram import inject

router = Router(name="start")


@router.message(CommandStart())
@inject
async def cmd_start(
    message: types.Message,
    user_service: FromDishka[UserServiceInterface],
):
    create_entity = CreateUserEntity.from_aiogram(message.from_user)
    user = await user_service.get_or_create(create_entity)

    welcome_text = (
        f"\n👋 <b>Привет, {user.display_name}!</b>\n\n"
        "Я помогу следить за новыми записями на Яндекс.Диске.\n"
        "Чтобы получать уведомления, нажми команду <b>/set</b> и укажи группу."
    )

    await message.answer(welcome_text, parse_mode="HTML")
