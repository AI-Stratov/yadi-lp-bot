from datetime import time

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from bot.application.widgets.time_picker import (
    build_time_keyboard,
    handle_time_callback,
)
from bot.domain.entities.mappings import SUBJECTS, NotificationScheduleMode, iter_subjects_for_course
from bot.domain.entities.states import NotificationSettingsStates
from bot.domain.entities.user import UpdateUserEntity, UserEntity
from bot.domain.services.user import UserServiceInterface

router = Router(name="notification_settings")


def _fmt_time(t: time | None) -> str:
    return t.strftime("%H:%M") if t else ""


def _time_to_str(t: time) -> str:
    return t.strftime("%H:%M")


def _str_to_time(s: str | None, default: time) -> time:
    if not s:
        return default
    try:
        hh, mm = s.split(":")
        return time(int(hh), int(mm))
    except Exception:
        return default


def _mode_label(user: UserEntity) -> str:
    mode = user.notification_mode
    if mode == NotificationScheduleMode.ASAP:
        return "⚡ Режим: сразу"
    if mode == NotificationScheduleMode.AT_TIME:
        return "⏰ Режим: время"
    if mode == NotificationScheduleMode.IN_WINDOW:
        return "🪟 Режим: промежуток"
    return "⚙️ Режим: выбрать"


def build_modes_kb(current: NotificationScheduleMode | None) -> types.InlineKeyboardMarkup:
    """Клавиатура выбора режима доставки уведомлений."""
    kb = InlineKeyboardBuilder()

    def mark(mode: NotificationScheduleMode) -> str:
        return "✅ " if current == mode else ""

    kb.row(
        InlineKeyboardButton(text=f"{mark(NotificationScheduleMode.ASAP)}⚡ Сразу", callback_data="mode:ASAP"),
    )
    kb.row(
        InlineKeyboardButton(text=f"{mark(NotificationScheduleMode.AT_TIME)}⏰ В определённое время", callback_data="mode:AT_TIME"),
    )
    kb.row(
        InlineKeyboardButton(text=f"{mark(NotificationScheduleMode.IN_WINDOW)}🪟 В промежутке", callback_data="mode:IN_WINDOW"),
    )
    kb.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
    )
    kb.adjust(1)
    return kb.as_markup()


def build_settings_kb(user: UserEntity) -> types.InlineKeyboardMarkup:
    """Главное меню настроек уведомлений."""
    kb = InlineKeyboardBuilder()

    # Переключатель уведомлений
    notif_mark = "🟢 Вкл" if user.enable_notifications else "🔴 Выкл"
    kb.row(InlineKeyboardButton(text=f"🔔 Уведомления: {notif_mark}", callback_data="toggle_notifications"))

    # Режим доставки
    kb.row(InlineKeyboardButton(text=f"{_mode_label(user)}", callback_data="choose_mode"))

    # Дополнительные настройки по выбранному режиму
    if user.notification_mode == NotificationScheduleMode.AT_TIME:
        t = _fmt_time(user.task_send_time) or "—"
        kb.row(InlineKeyboardButton(text=f"⏰ Время: {t}", callback_data="set_time"))
    elif user.notification_mode == NotificationScheduleMode.IN_WINDOW:
        s = _fmt_time(user.delivery_window_start) or "—"
        e = _fmt_time(user.delivery_window_end) or "—"
        kb.row(InlineKeyboardButton(text=f"🪟 Окно: {s}–{e}", callback_data="set_window"))

    # Предметы: показываем количество активных (всего по курсу минус исключённые)
    subjects_label = "📚 Предметы"
    try:
        if user.user_course:
            total = len([key for key, _ in iter_subjects_for_course(user.user_course)])
            excluded_cnt = len(user.excluded_disciplines or set())
            active_cnt = max(total - excluded_cnt, 0)
            subjects_label = f"📚 Предметы ({active_cnt})"
    except Exception:
        # в случае любой ошибки — не ломаем меню, показываем базовую надпись
        pass

    kb.row(InlineKeyboardButton(text=subjects_label, callback_data="subjects"))

    kb.adjust(1)
    return kb.as_markup()


def _build_subjects_keyboard(*, subject_keys: list[str], excluded_keys: set[str], page: int) -> types.InlineKeyboardMarkup:
    """Пагинированная клавиатура для выбора исключаемых предметов.
    subject_keys — список ключей (папок на диске), excluded_keys — текущие исключённые.
    Зеленая точка — предмет включён; красная — исключён.
    """
    page_size = SUBJECTS_PAGE_SIZE
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_keys = subject_keys[start_idx:end_idx]

    kb = InlineKeyboardBuilder()

    # Кнопки по 2 в строке
    for i in range(0, len(page_keys), 2):
        row = []
        for key in page_keys[i: i + 2]:
            display = SUBJECTS.get(key, key)
            is_excluded = key in excluded_keys
            mark = "🔴" if is_excluded else "🟢"
            row.append(
                InlineKeyboardButton(
                    text=f"{mark} {display}",
                    callback_data=f"subj_toggle:{key}",
                )
            )
        kb.row(*row)

    # Навигация
    has_prev = page > 0
    has_next = end_idx < len(subject_keys)
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"subj_page:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"subj_page:{page + 1}"))
    if nav:
        kb.row(*nav)

    # Действия
    kb.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="subj_done"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="subj_cancel"),
    )

    return kb.as_markup()


@router.message(Command("settings"))
@inject
async def open_settings(
    message: types.Message,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await state.clear()
    from bot.domain.entities.user import CreateUserEntity

    user = await user_service.get_or_create(CreateUserEntity.from_aiogram(message.from_user))

    await message.answer("⚙️ Настройки уведомлений", reply_markup=build_settings_kb(user))
    await state.set_state(NotificationSettingsStates.menu)


@router.callback_query(NotificationSettingsStates.menu, F.data == "toggle_notifications")
@inject
async def toggle_notifications(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer()
    user = await user_service.get_user_by_id(callback.from_user.id)
    if not user:
        return

    update = UpdateUserEntity(enable_notifications=not user.enable_notifications)
    user = await user_service.update_user(callback.from_user.id, update)

    await callback.message.edit_reply_markup(reply_markup=build_settings_kb(user))


@router.callback_query(NotificationSettingsStates.menu, F.data == "choose_mode")
@inject
async def choose_mode(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer()
    user = await user_service.get_user_by_id(callback.from_user.id)
    if not user:
        return
    await callback.message.edit_text(
        "В какое время приходят уведомления?",
        reply_markup=build_modes_kb(user.notification_mode),
    )
    await state.set_state(NotificationSettingsStates.choosing_mode)


@router.callback_query(NotificationSettingsStates.choosing_mode, F.data.startswith("mode:"))
@inject
async def set_mode(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer()
    mode_val = callback.data.split(":", 1)[1]
    try:
        mode = NotificationScheduleMode(mode_val)
    except ValueError:
        return

    update = UpdateUserEntity(notification_mode=mode)
    if mode == NotificationScheduleMode.ASAP:
        update.task_send_time = None
        update.delivery_window_start = None
        update.delivery_window_end = None

    user = await user_service.update_user(callback.from_user.id, update)

    await callback.message.edit_text(
        "⚙️ Настройки уведомлений",
        reply_markup=build_settings_kb(user),
    )
    await state.set_state(NotificationSettingsStates.menu)


@router.callback_query(NotificationSettingsStates.choosing_mode, F.data == "back_to_menu")
@inject
async def back_to_menu_from_mode(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer()
    user = await user_service.get_user_by_id(callback.from_user.id)
    if not user:
        return
    await callback.message.edit_text(
        "⚙️ Настройки уведомлений",
        reply_markup=build_settings_kb(user),
    )
    await state.set_state(NotificationSettingsStates.menu)


@router.callback_query(NotificationSettingsStates.menu, F.data == "set_time")
@inject
async def start_pick_time(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer()
    user = await user_service.get_user_by_id(callback.from_user.id)

    # Разрешаем выбор времени только если режим AT_TIME
    if not user or user.notification_mode != NotificationScheduleMode.AT_TIME:
        await callback.message.edit_text(
            "В какое время приходят уведомления?",
            reply_markup=build_modes_kb(user.notification_mode if user else None),
        )
        await state.set_state(NotificationSettingsStates.choosing_mode)
        return

    current_time_obj = user.task_send_time if user.task_send_time else time(10, 0)
    await state.update_data(current_time=_time_to_str(current_time_obj))
    await callback.message.edit_text(
        "⏰ Выбор времени",
        reply_markup=build_time_keyboard(current_time_obj, prefix="tp"),
    )
    await state.set_state(NotificationSettingsStates.picking_time)


@router.callback_query(NotificationSettingsStates.picking_time, F.data.startswith("tp:"))
@inject
async def handle_time_picker(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    data = await state.get_data()
    cur = _str_to_time(data.get("current_time"), default=time(10, 0))

    cur, action = handle_time_callback(callback.data, cur, prefix="tp")

    if action == "update":
        await state.update_data(current_time=_time_to_str(cur))
        await callback.message.edit_text(
            "⏰ Выбор времени",
            reply_markup=build_time_keyboard(cur, prefix="tp"),
        )
        await callback.answer()
        return
    if action == "confirm":
        update = UpdateUserEntity(task_send_time=cur, notification_mode=NotificationScheduleMode.AT_TIME)
        user = await user_service.update_user(callback.from_user.id, update)
        await state.set_state(NotificationSettingsStates.menu)
        await state.set_data({})
        await callback.message.edit_text(
            "⚙️ Настройки уведомлений",
            reply_markup=build_settings_kb(user),
        )
        await callback.answer("Время обновлено")
        return
    if action == "cancel":
        await state.set_state(NotificationSettingsStates.menu)
        await state.set_data({})
        user = await user_service.get_user_by_id(callback.from_user.id)
        if user:
            await callback.message.edit_text(
                "⚙️ Настройки уведомлений",
                reply_markup=build_settings_kb(user),
            )
        await callback.answer("Отменено")
        return


@router.callback_query(NotificationSettingsStates.menu, F.data == "set_window")
@inject
async def start_pick_window_start(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer()
    user = await user_service.get_user_by_id(callback.from_user.id)

    # Разрешаем выбор промежутка только если режим IN_WINDOW
    if not user or user.notification_mode != NotificationScheduleMode.IN_WINDOW:
        await callback.message.edit_text(
            "В какое время приходят уведомления?",
            reply_markup=build_modes_kb(user.notification_mode if user else None),
        )
        await state.set_state(NotificationSettingsStates.choosing_mode)
        return

    start_obj = user.delivery_window_start if user.delivery_window_start else time(10, 0)
    end_prev_obj = user.delivery_window_end if user.delivery_window_end else None
    await state.update_data(
        window_start=_time_to_str(start_obj),
        window_end_prev=_time_to_str(end_prev_obj) if end_prev_obj else None,
    )
    await callback.message.edit_text(
        "🪟 Начало промежутка",
        reply_markup=build_time_keyboard(start_obj, prefix="tp"),
    )
    await state.set_state(NotificationSettingsStates.picking_window_start)


@router.callback_query(NotificationSettingsStates.picking_window_start, F.data.startswith("tp:"))
@inject
async def handle_window_start(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    data = await state.get_data()
    cur = _str_to_time(data.get("window_start"), default=time(10, 0))

    cur, action = handle_time_callback(callback.data, cur, prefix="tp")

    if action == "update":
        await state.update_data(window_start=_time_to_str(cur))
        await callback.message.edit_text(
            "🪟 Начало промежутка",
            reply_markup=build_time_keyboard(cur, prefix="tp"),
        )
        await callback.answer()
        return
    if action == "confirm":
        prev_end = _str_to_time((await state.get_data()).get("window_end_prev"), default=time((cur.hour + 1) % 24, cur.minute))
        end_initial = prev_end
        await state.update_data(window_start=_time_to_str(cur), current_time=_time_to_str(end_initial))
        await callback.message.edit_text(
            "🪟 Конец промежутка",
            reply_markup=build_time_keyboard(end_initial, prefix="tp"),
        )
        await state.set_state(NotificationSettingsStates.picking_window_end)
        await callback.answer()
        return
    if action == "cancel":
        await state.set_state(NotificationSettingsStates.menu)
        await state.set_data({})
        user = await user_service.get_user_by_id(callback.from_user.id)
        if user:
            await callback.message.edit_text(
                "⚙️ Настройки уведомлений",
                reply_markup=build_settings_kb(user),
            )
        await callback.answer("Отменено")
        return


@router.callback_query(NotificationSettingsStates.picking_window_end, F.data.startswith("tp:"))
@inject
async def handle_window_end(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    data = await state.get_data()
    cur = _str_to_time(data.get("current_time"), default=time(11, 0))

    cur, action = handle_time_callback(callback.data, cur, prefix="tp")

    if action == "update":
        await state.update_data(current_time=_time_to_str(cur))
        await callback.message.edit_text(
            "🪟 Конец промежутка",
            reply_markup=build_time_keyboard(cur, prefix="tp"),
        )
        await callback.answer()
        return
    if action == "confirm":
        start_t = _str_to_time((await state.get_data()).get("window_start"), default=time(10, 0))
        update = UpdateUserEntity(
            delivery_window_start=start_t,
            delivery_window_end=cur,
            notification_mode=NotificationScheduleMode.IN_WINDOW,
        )
        user = await user_service.update_user(callback.from_user.id, update)
        await state.set_state(NotificationSettingsStates.menu)
        await state.set_data({})
        await callback.message.edit_text(
            "⚙️ Настройки уведомлений",
            reply_markup=build_settings_kb(user),
        )
        await callback.answer("Промежуток обновлён")
        return
    if action == "cancel":
        await state.set_state(NotificationSettingsStates.menu)
        await state.set_data({})
        user = await user_service.get_user_by_id(callback.from_user.id)
        if user:
            await callback.message.edit_text(
                "⚙️ Настройки уведомлений",
                reply_markup=build_settings_kb(user),
            )
        await callback.answer("Отменено")
        return


# -------- Предметы: выбор/пагинация/подтверждение --------

SUBJECTS_PAGE_SIZE = 10


@router.callback_query(NotificationSettingsStates.menu, F.data == "subjects")
@inject
async def subjects_open(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer()
    user = await user_service.get_user_by_id(callback.from_user.id)
    if not user or not user.user_course:
        await callback.message.edit_text(
            "Сначала выберите курс через /set",
            reply_markup=build_settings_kb(user) if user else None,
        )
        return

    # соберём список ключей предметов для курса
    subj_keys = [key for key, _ in iter_subjects_for_course(user.user_course)]
    excluded_current = set(user.excluded_disciplines or [])

    # сохраняем в состоянии JSON‑безопасно (списки)
    await state.set_state(NotificationSettingsStates.picking_subjects)
    await state.set_data({
        "subj_all_keys": subj_keys,
        "subj_excluded": list(excluded_current),
        "subj_page": 0,
    })

    kb = _build_subjects_keyboard(subject_keys=subj_keys, excluded_keys=excluded_current, page=0)
    await callback.message.edit_text("📚 Исключить предметы", reply_markup=kb)


@router.callback_query(NotificationSettingsStates.picking_subjects, F.data.startswith("subj_toggle:"))
async def subjects_toggle(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    key = callback.data.split(":", 1)[1]

    subj_keys: list[str] = data.get("subj_all_keys", [])
    excluded_list: list[str] = data.get("subj_excluded", [])
    excluded = set(excluded_list)

    if key in excluded:
        excluded.remove(key)
    else:
        excluded.add(key)

    page = int(data.get("subj_page", 0))

    await state.update_data(subj_excluded=list(excluded))
    kb = _build_subjects_keyboard(subject_keys=subj_keys, excluded_keys=excluded, page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(NotificationSettingsStates.picking_subjects, F.data.startswith("subj_page:"))
async def subjects_page(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    page = int(callback.data.split(":", 1)[1])
    subj_keys: list[str] = data.get("subj_all_keys", [])
    excluded_list: list[str] = data.get("subj_excluded", [])
    excluded = set(excluded_list)

    await state.update_data(subj_page=page)
    kb = _build_subjects_keyboard(subject_keys=subj_keys, excluded_keys=excluded, page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(NotificationSettingsStates.picking_subjects, F.data == "subj_cancel")
@inject
async def subjects_cancel(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer("Отменено")
    await state.set_state(NotificationSettingsStates.menu)
    await state.set_data({})
    user = await user_service.get_user_by_id(callback.from_user.id)
    if user:
        await callback.message.edit_text("⚙️ Настройки уведомлений", reply_markup=build_settings_kb(user))


@router.callback_query(NotificationSettingsStates.picking_subjects, F.data == "subj_done")
@inject
async def subjects_done(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    await callback.answer()
    data = await state.get_data()
    excluded_list: list[str] = data.get("subj_excluded", [])

    user = await user_service.update_user(
        callback.from_user.id,
        UpdateUserEntity(excluded_disciplines=set(excluded_list)),
    )

    await state.set_state(NotificationSettingsStates.menu)
    await state.set_data({})

    await callback.message.edit_text("⚙️ Настройки уведомлений", reply_markup=build_settings_kb(user))
    await callback.answer("Предметы обновлены")
