from datetime import time

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from bot.application.widgets.time_picker import TimePicker
from bot.application.widgets.keyboards import (
    build_notification_modes_kb,
    build_notification_settings_kb,
    build_subjects_selection_kb,
)
from bot.domain.entities.constants import SUBJECTS_PAGE_SIZE
from bot.domain.entities.mappings import iter_subjects_for_course, NotificationScheduleMode
from bot.domain.entities.states import NotificationSettingsStates
from bot.domain.entities.user import UpdateUserEntity
from bot.domain.services.user import UserServiceInterface
from bot.common.utils.formatting import time_to_str, str_to_time

router = Router(name="notification_settings")


@router.message(Command("settings"))
@inject
async def open_settings(
    message: types.Message,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    """Открыть меню настроек уведомлений."""
    await state.clear()
    from bot.domain.entities.user import CreateUserEntity

    user = await user_service.get_or_create(CreateUserEntity.from_aiogram(message.from_user))

    await message.answer("⚙️ Настройки уведомлений", reply_markup=build_notification_settings_kb(user))
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

    await callback.message.edit_reply_markup(reply_markup=build_notification_settings_kb(user))


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
        reply_markup=build_notification_modes_kb(user.notification_mode),
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
        reply_markup=build_notification_settings_kb(user),
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
        reply_markup=build_notification_settings_kb(user),
    )
    await state.set_state(NotificationSettingsStates.menu)


@router.callback_query(NotificationSettingsStates.menu, F.data == "set_time")
@inject
async def start_pick_time(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
    time_picker: FromDishka[TimePicker],
):
    await callback.answer()
    user = await user_service.get_user_by_id(callback.from_user.id)

    # Разрешаем выбор времени только если режим AT_TIME
    if not user or user.notification_mode != NotificationScheduleMode.AT_TIME:
        await callback.message.edit_text(
            "В какое время приходят уведомления?",
            reply_markup=build_notification_modes_kb(user.notification_mode if user else None),
        )
        await state.set_state(NotificationSettingsStates.choosing_mode)
        return

    current_time_obj = user.task_send_time if user.task_send_time else time(10, 0)
    await state.update_data(current_time=time_to_str(current_time_obj))
    await callback.message.edit_text(
        "⏰ Выбор времени",
        reply_markup=time_picker.build_keyboard(current_time_obj),
    )
    await state.set_state(NotificationSettingsStates.picking_time)


@router.callback_query(NotificationSettingsStates.picking_time, F.data.startswith("tp:"))
@inject
async def handle_time_picker(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
    time_picker: FromDishka[TimePicker],
):
    data = await state.get_data()
    cur = str_to_time(data.get("current_time"), default=time(10, 0))

    cur, action = time_picker.handle_callback(callback.data, cur)

    if action == "update":
        await state.update_data(current_time=time_to_str(cur))
        await callback.message.edit_reply_markup(reply_markup=time_picker.build_keyboard(cur))
        await callback.answer()
    elif action == "confirm":
        update = UpdateUserEntity(task_send_time=cur)
        user = await user_service.update_user(callback.from_user.id, update)
        await callback.message.edit_text("⚙️ Настройки уведомлений", reply_markup=build_notification_settings_kb(user))
        await state.set_state(NotificationSettingsStates.menu)
        await callback.answer()
    elif action == "cancel":
        user = await user_service.get_user_by_id(callback.from_user.id)
        if user:
            await callback.message.edit_text("⚙️ Настройки уведомлений", reply_markup=build_notification_settings_kb(user))
        await state.set_state(NotificationSettingsStates.menu)
        await callback.answer()


@router.callback_query(NotificationSettingsStates.menu, F.data == "set_window")
@inject
async def start_pick_window_start(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
    time_picker: FromDishka[TimePicker],
):
    await callback.answer()
    user = await user_service.get_user_by_id(callback.from_user.id)

    # Разрешаем выбор промежутка только если режим IN_WINDOW
    if not user or user.notification_mode != NotificationScheduleMode.IN_WINDOW:
        await callback.message.edit_text(
            "В какое время приходят уведомления?",
            reply_markup=build_notification_modes_kb(user.notification_mode if user else None),
        )
        await state.set_state(NotificationSettingsStates.choosing_mode)
        return

    start_obj = user.delivery_window_start if user.delivery_window_start else time(10, 0)
    end_prev_obj = user.delivery_window_end if user.delivery_window_end else None
    await state.update_data(
        window_start=time_to_str(start_obj),
        window_end_prev=time_to_str(end_prev_obj) if end_prev_obj else None,
    )
    await callback.message.edit_text(
        "🪟 Начало промежутка",
        reply_markup=time_picker.build_keyboard(start_obj),
    )
    await state.set_state(NotificationSettingsStates.picking_window_start)


@router.callback_query(NotificationSettingsStates.picking_window_start, F.data.startswith("tp:"))
@inject
async def handle_window_start(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
    time_picker: FromDishka[TimePicker],
):
    data = await state.get_data()
    cur = str_to_time(data.get("window_start"), default=time(10, 0))

    cur, action = time_picker.handle_callback(callback.data, cur)

    if action == "update":
        await state.update_data(window_start=time_to_str(cur))
        await callback.message.edit_text(
            "🪟 Начало промежутка",
            reply_markup=time_picker.build_keyboard(cur),
        )
        await callback.answer()
    elif action == "confirm":
        prev_end = str_to_time((await state.get_data()).get("window_end_prev"), default=time((cur.hour + 1) % 24, cur.minute))
        end_initial = prev_end
        await state.update_data(window_start=time_to_str(cur), current_time=time_to_str(end_initial))
        await callback.message.edit_text(
            "🪟 Конец промежутка",
            reply_markup=time_picker.build_keyboard(end_initial),
        )
        await state.set_state(NotificationSettingsStates.picking_window_end)
        await callback.answer()
    elif action == "cancel":
        await state.set_state(NotificationSettingsStates.menu)
        await state.set_data({})
        user = await user_service.get_user_by_id(callback.from_user.id)
        if user:
            await callback.message.edit_text(
                "⚙️ Настройки уведомлений",
                reply_markup=build_notification_settings_kb(user),
            )
        await callback.answer("Отменено")
        return


@router.callback_query(NotificationSettingsStates.picking_window_end, F.data.startswith("tp:"))
@inject
async def handle_window_end(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
    time_picker: FromDishka[TimePicker],
):
    data = await state.get_data()
    cur = str_to_time(data.get("current_time"), default=time(11, 0))

    cur, action = time_picker.handle_callback(callback.data, cur)

    if action == "update":
        await state.update_data(current_time=time_to_str(cur))
        await callback.message.edit_text(
            "🪟 Конец промежутка",
            reply_markup=time_picker.build_keyboard(cur),
        )
        await callback.answer()
    elif action == "confirm":
        start_t = str_to_time((await state.get_data()).get("window_start"), default=time(10, 0))
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
            reply_markup=build_notification_settings_kb(user),
        )
        await callback.answer("Промежуток обновлён")
    elif action == "cancel":
        await state.set_state(NotificationSettingsStates.menu)
        await state.set_data({})
        user = await user_service.get_user_by_id(callback.from_user.id)
        if user:
            await callback.message.edit_text(
                "⚙️ Настройки уведомлений",
                reply_markup=build_notification_settings_kb(user),
            )
        await callback.answer("Отменено")
        return


# -------- Предметы: выбор/пагинация/подтверждение --------

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
            reply_markup=build_notification_settings_kb(user) if user else None,
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

    kb = build_subjects_selection_kb(
        subject_keys=subj_keys,
        excluded_keys=excluded_current,
        page=0,
        page_size=SUBJECTS_PAGE_SIZE
    )
    await callback.message.edit_text("📚 Исключить предметы", reply_markup=kb)


@router.callback_query(NotificationSettingsStates.picking_subjects, F.data.startswith("subj_toggle:"))
async def subjects_toggle(callback: types.CallbackQuery, state: FSMContext):
    """Обратная совместимость: старый формат subj_toggle:{key}."""
    await callback.answer()
    data = await state.get_data()
    key = callback.data.split(":", 1)[1]

    subj_keys: list[str] = data.get("subj_all_keys", [])
    excluded_list: list[str] = data.get("subj_excluded", [])
    excluded = set(excluded_list)

    if key in excluded:
        excluded.remove(key)
    else:
        if key in subj_keys:
            excluded.add(key)
        else:
            return

    page = int(data.get("subj_page", 0))

    await state.update_data(subj_excluded=list(excluded))
    kb = build_subjects_selection_kb(
        subject_keys=subj_keys,
        excluded_keys=excluded,
        page=page,
        page_size=SUBJECTS_PAGE_SIZE
    )
    await callback.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(NotificationSettingsStates.picking_subjects, F.data.startswith("subj_ti:"))
async def subjects_toggle_index(callback: types.CallbackQuery, state: FSMContext):
    """Новый формат: subj_ti:{index} — короткий callback_data для Telegram."""
    await callback.answer()
    data = await state.get_data()
    try:
        idx = int(callback.data.split(":", 1)[1])
    except Exception:
        return

    subj_keys: list[str] = data.get("subj_all_keys", [])
    if not (0 <= idx < len(subj_keys)):
        return
    key = subj_keys[idx]

    excluded_list: list[str] = data.get("subj_excluded", [])
    excluded = set(excluded_list)

    if key in excluded:
        excluded.remove(key)
    else:
        excluded.add(key)

    page = int(data.get("subj_page", 0))

    await state.update_data(subj_excluded=list(excluded))
    kb = build_subjects_selection_kb(
        subject_keys=subj_keys,
        excluded_keys=excluded,
        page=page,
        page_size=SUBJECTS_PAGE_SIZE
    )
    await callback.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(NotificationSettingsStates.picking_subjects, F.data.startswith("subj_page:"))
async def subjects_page(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    try:
        page = int(callback.data.split(":", 1)[1])
    except Exception:
        page = 0
    subj_keys: list[str] = data.get("subj_all_keys", [])
    excluded_list: list[str] = data.get("subj_excluded", [])
    excluded = set(excluded_list)

    await state.update_data(subj_page=page)
    kb = build_subjects_selection_kb(
        subject_keys=subj_keys,
        excluded_keys=excluded,
        page=page,
        page_size=SUBJECTS_PAGE_SIZE
    )
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
        await callback.message.edit_text("⚙️ Настройки уведомлений", reply_markup=build_notification_settings_kb(user))


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

    await callback.message.edit_text("⚙️ Настройки уведомлений", reply_markup=build_notification_settings_kb(user))
    await callback.answer("Предметы обновлены")
