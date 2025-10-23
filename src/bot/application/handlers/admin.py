from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from bot.application.widgets.keyboards import build_roles_menu_kb
from bot.common.utils.pagination import paginate
from bot.common.utils.permissions import is_superuser
from bot.common.utils.sorting import sort_users
from bot.domain.entities import constants as app_consts
from bot.domain.entities.mappings import UserType
from bot.domain.entities.user import CreateUserEntity
from bot.domain.services.user import UserServiceInterface

router = Router(name="roles")


async def _build_role_list_page(user_service: UserServiceInterface, role_choice: str, page: int) -> tuple[str, InlineKeyboardMarkup]:
    """
    Построить страницу списка пользователей по роли.

    Args:
        user_service: Сервис пользователей
        role_choice: Выбранная роль (users/admins)
        page: Номер страницы

    Returns:
        tuple[str, InlineKeyboardMarkup]: Текст сообщения и клавиатура
    """
    if role_choice == "users":
        role_type = UserType.USER
        header = "👥 Пользователи"
        action_label = "Сделать ADMIN"
        new_role = UserType.ADMIN
    elif role_choice == "admins":
        role_type = UserType.ADMIN
        header = "🛡️ Администраторы"
        action_label = "Сделать USER"
        new_role = UserType.USER
    else:
        role_type = UserType.USER
        header = "👥 Пользователи"
        action_label = "Сделать ADMIN"
        new_role = UserType.ADMIN

    users = await user_service.get_users_by_type(role_type)
    users = sort_users(users)

    pg = paginate(users, page, app_consts.PAGE_SIZE)

    lines: list[str] = [f"{header} — страница {pg.page + 1}/{pg.total_pages}", f"Всего: {pg.total_items}", ""]

    kb = InlineKeyboardBuilder()

    if pg.total_items == 0:
        lines.append("Список пуст. Откройте вкладку 'Все', чтобы увидеть всех пользователей.")
    else:
        for u in pg.items:
            name = u.display_name
            lines.append(f"• {name} (ID: {u.tg_id})")
            # Кнопка смены роли
            kb.row(
                InlineKeyboardButton(
                    text=f"{action_label} — {name}",
                    callback_data=f"roles:set:{u.tg_id}:{new_role}:{role_choice}:{pg.page}",
                )
            )

    # Навигация
    nav_row = []
    if pg.has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"roles:view:{role_choice}:page:{pg.page - 1}"))
    if pg.has_next:
        nav_row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"roles:view:{role_choice}:page:{pg.page + 1}"))
    if nav_row:
        kb.row(*nav_row)

    # Возврат в меню
    kb.row(InlineKeyboardButton(text="🏠 Меню", callback_data="roles:menu"))

    return "\n".join(lines), kb.as_markup()


async def _build_all_list_page(user_service: UserServiceInterface, page: int) -> tuple[str, InlineKeyboardMarkup]:
    """
    Построить страницу списка всех пользователей.

    Args:
        user_service: Сервис пользователей
        page: Номер страницы

    Returns:
        tuple[str, InlineKeyboardMarkup]: Текст сообщения и клавиатура
    """
    users = await user_service.list_all_users()
    users = sort_users(users)

    pg = paginate(users, page, app_consts.PAGE_SIZE)

    lines: list[str] = [f"📋 Все пользователи — страница {pg.page + 1}/{pg.total_pages}", f"Всего: {pg.total_items}", ""]

    kb = InlineKeyboardBuilder()

    if pg.total_items == 0:
        lines.append("Пока нет ни одного пользователя.")
    else:
        for u in pg.items:
            role = getattr(u, "user_type", UserType.USER)
            name = u.display_name
            role_label = "SUPERUSER" if role == UserType.SUPERUSER else ("ADMIN" if role == UserType.ADMIN else "USER")
            lines.append(f"• {name} (ID: {u.tg_id}) — {role_label}")
            # Кнопки смены ролей только между USER/ADMIN
            if role != UserType.SUPERUSER:
                if role == UserType.ADMIN:
                    kb.row(
                        InlineKeyboardButton(
                            text=f"Сделать USER — {name}",
                            callback_data=f"roles:set:{u.tg_id}:{UserType.USER}:all:{pg.page}",
                        )
                    )
                elif role == UserType.USER:
                    kb.row(
                        InlineKeyboardButton(
                            text=f"Сделать ADMIN — {name}",
                            callback_data=f"roles:set:{u.tg_id}:{UserType.ADMIN}:all:{pg.page}",
                        )
                    )

    # Навигация
    nav_row = []
    if pg.has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"roles:view:all:page:{pg.page - 1}"))
    if pg.has_next:
        nav_row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"roles:view:all:page:{pg.page + 1}"))
    if nav_row:
        kb.row(*nav_row)

    # Возврат в меню
    kb.row(InlineKeyboardButton(text="🏠 Меню", callback_data="roles:menu"))

    return "\n".join(lines), kb.as_markup()


@router.message(Command("roles"))
@inject
async def cmd_roles(
    message: types.Message,
    user_service: FromDishka[UserServiceInterface],
):
    """Открыть меню управления ролями (только для суперпользователя)."""
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(message.from_user))
    if not is_superuser(caller):
        await message.reply("🚫 Доступно только суперпользователю")
        return

    await message.answer("⭐ Управление ролями", reply_markup=build_roles_menu_kb())


@router.callback_query(F.data == "roles:menu")
@inject
async def cb_roles_menu(
    cq: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
):
    """Вернуться в главное меню ролей."""
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(cq.from_user))
    if not is_superuser(caller):
        await cq.answer("Нет доступа", show_alert=True)
        return
    try:
        await cq.message.edit_text("⭐ Управление ролями", reply_markup=build_roles_menu_kb())
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await cq.answer()


@router.callback_query(F.data.startswith("roles:view:"))
@inject
async def cb_roles_view(
    cq: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
):
    """Просмотр списка пользователей по роли."""
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(cq.from_user))
    if not is_superuser(caller):
        await cq.answer("Нет доступа", show_alert=True)
        return

    # Формат: roles:view:{role_choice}:page:{n}
    try:
        _, _, role_choice, _, page_s = cq.data.split(":", 4)
        page = int(page_s)
    except Exception: # pylint: disable=broad-except
        role_choice = "users"
        page = 0

    if role_choice == "all":
        text, markup = await _build_all_list_page(user_service, page)
    else:
        text, markup = await _build_role_list_page(user_service, role_choice, page)
    try:
        await cq.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await cq.answer()


@router.callback_query(F.data.startswith("roles:set:"))
@inject
async def cb_roles_set(
    cq: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
):
    """Изменить роль пользователя."""
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(cq.from_user))
    if not is_superuser(caller):
        await cq.answer("Нет доступа", show_alert=True)
        return

    # Формат: roles:set:{tg_id}:{role}:{role_choice}:{page}
    try:
        _, _, tg_id_s, role_s, role_choice, page_s = cq.data.split(":", 5)
        target_id = int(tg_id_s)
        new_role = UserType(role_s)
        page = int(page_s)
    except Exception: # pylint: disable=broad-except
        await cq.answer("Некорректный запрос", show_alert=True)
        return

    # Без возможности менять роль SUPERUSER
    tu = await user_service.get_user_by_id(target_id)
    if tu and getattr(tu, "user_type", None) == UserType.SUPERUSER:
        await cq.answer("Нельзя изменять роль SUPERUSER", show_alert=True)
        return

    await user_service.set_user_type(target_id, new_role)

    # Обновляем текущий список
    if role_choice == "all":
        text, markup = await _build_all_list_page(user_service, page)
    else:
        text, markup = await _build_role_list_page(user_service, role_choice, page)
    try:
        await cq.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await cq.answer("Обновлено")
