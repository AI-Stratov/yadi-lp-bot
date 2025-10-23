"""Билдеры клавиатур для Telegram UI."""
from aiogram import types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.domain.entities.course import Course, get_courses
from bot.domain.entities.mappings import SUBJECTS, NotificationScheduleMode
from bot.domain.entities.user import UserEntity
from bot.common.utils.formatting import fmt_time, fmt_int


# ============================================================================
# Клавиатуры для выбора курса и группы (/set)
# ============================================================================

def build_courses_kb() -> types.InlineKeyboardMarkup:
    """
    Клавиатура выбора курса

    :return: inline-клавиатура со списком доступных курсов
    """
    kb = InlineKeyboardBuilder()
    for code, course in get_courses().items():
        kb.button(text=course.title, callback_data=f"course:{code}")
    kb.adjust(2)
    return kb.as_markup()


def build_groups_kb(course: Course) -> types.InlineKeyboardMarkup:
    """
    Клавиатура выбора группы для конкретного курса

    :param course: объект курса с доступными группами
    :return: inline-клавиатура со списком групп курса
    """
    kb = InlineKeyboardBuilder()
    for group in course.groups:
        kb.button(text=f"{group}", callback_data=f"group:{course.code}:{group}")
    kb.adjust(3)
    return kb.as_markup()


# ============================================================================
# Клавиатуры настроек уведомлений (/settings)
# ============================================================================

def build_notification_modes_kb(current: NotificationScheduleMode | None) -> types.InlineKeyboardMarkup:
    """
    Клавиатура выбора режима доставки уведомлений

    :param current: текущий выбранный режим (для отметки галочкой)
    :return: inline-клавиатура с режимами доставки
    """
    kb = InlineKeyboardBuilder()

    def mark(mode: NotificationScheduleMode) -> str:
        return "✅ " if current == mode else ""

    kb.row(
        InlineKeyboardButton(text=f"{mark(NotificationScheduleMode.ASAP)}⚡ Сразу", callback_data="mode:ASAP"),
    )
    kb.row(
        InlineKeyboardButton(
            text=f"{mark(NotificationScheduleMode.AT_TIME)}⏰ В определённое время",
            callback_data="mode:AT_TIME"
        ),
    )
    kb.row(
        InlineKeyboardButton(
            text=f"{mark(NotificationScheduleMode.IN_WINDOW)}🪟 В промежутке",
            callback_data="mode:IN_WINDOW"
        ),
    )
    kb.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
    )
    kb.adjust(1)
    return kb.as_markup()


def build_notification_settings_kb(user: UserEntity) -> types.InlineKeyboardMarkup:
    """
    Главное меню настроек уведомлений

    :param user: сущность пользователя для отображения текущих настроек
    :return: inline-клавиатура с меню настроек
    """
    def get_mode_label(u: UserEntity) -> str:
        """Получить метку текущего режима доставки."""
        mode = u.notification_mode
        if mode == NotificationScheduleMode.ASAP:
            return "⚡ Режим: сразу"
        if mode == NotificationScheduleMode.AT_TIME:
            return "⏰ Режим: время"
        if mode == NotificationScheduleMode.IN_WINDOW:
            return "🪟 Режим: промежуток"
        return "⚙️ Режим: выбрать"

    kb = InlineKeyboardBuilder()

    # Переключатель уведомлений
    notif_mark = "🟢 Вкл" if user.enable_notifications else "🔴 Выкл"
    kb.row(InlineKeyboardButton(text=f"🔔 Уведомления: {notif_mark}", callback_data="toggle_notifications"))

    # Режим доставки
    kb.row(InlineKeyboardButton(text=get_mode_label(user), callback_data="choose_mode"))

    # Дополнительные настройки по выбранному режиму
    if user.notification_mode == NotificationScheduleMode.AT_TIME:
        t = fmt_time(user.task_send_time) or "-"
        kb.row(InlineKeyboardButton(text=f"⏰ Время: {t}", callback_data="set_time"))
    elif user.notification_mode == NotificationScheduleMode.IN_WINDOW:
        s = fmt_time(user.delivery_window_start) or "-"
        e = fmt_time(user.delivery_window_end) or "-"
        kb.row(InlineKeyboardButton(text=f"🪟 Окно: {s}–{e}", callback_data="set_window"))

    # Предметы: показываем количество активных (всего по курсу минус исключённые)
    subjects_label = "📚 Предметы"
    try:
        if user.user_course:
            from bot.domain.entities.mappings import iter_subjects_for_course
            total = len([key for key, _ in iter_subjects_for_course(user.user_course)])
            excluded_cnt = len(user.excluded_disciplines or set())
            active_cnt = max(total - excluded_cnt, 0)
            subjects_label = f"📚 Предметы ({active_cnt})"
    except Exception:
        # в случае любой ошибки - не ломаем меню, показываем базовую надпись
        pass

    kb.row(InlineKeyboardButton(text=subjects_label, callback_data="subjects"))

    kb.adjust(1)
    return kb.as_markup()


def build_subjects_selection_kb(
    *,
    subject_keys: list[str],
    excluded_keys: set[str],
    page: int,
    page_size: int = 8
) -> types.InlineKeyboardMarkup:
    """
    Пагинированная клавиатура для выбора исключаемых предметов

    :param subject_keys: список ключей предметов (папок на диске)
    :param excluded_keys: множество текущих исключённых предметов
    :param page: номер текущей страницы (начиная с 0)
    :param page_size: количество предметов на странице
    :return: inline-клавиатура с кнопками предметов и навигацией

    Зелёная точка — предмет включён; красная — исключён.
    callback_data использует индекс глобального списка для экономии символов.
    """
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_keys = subject_keys[start_idx:end_idx]

    kb = InlineKeyboardBuilder()

    # Кнопки по 2 в строке
    for i in range(0, len(page_keys), 2):
        row = []
        for offset, key in enumerate(page_keys[i: i + 2], start=i):
            display = SUBJECTS.get(key, key)
            is_excluded = key in excluded_keys
            mark = "🔴" if is_excluded else "🟢"
            global_index = start_idx + offset
            row.append(
                InlineKeyboardButton(
                    text=f"{mark} {display}",
                    callback_data=f"subj_ti:{global_index}",
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


# ============================================================================
# Клавиатуры статистики (/stats)
# ============================================================================

def build_stats_menu_kb() -> types.InlineKeyboardMarkup:
    """
    Главное меню статистики

    :return: inline-клавиатура с разделами статистики
    """
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📚 По курсам", callback_data="stats:courses:page:0"),
        InlineKeyboardButton(text="👥 По группам", callback_data="stats:groups:page:0"),
    )
    kb.row(InlineKeyboardButton(text="🚫 Отключённые", callback_data="stats:disabled"))
    kb.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="stats:refresh"))
    kb.adjust(2)
    return kb.as_markup()


def build_kv_list_kb(
    *,
    items: list[tuple[str, int]],
    page: int,
    back_cb: str,
    page_cb_prefix: str,
    page_size: int = 10
) -> types.InlineKeyboardMarkup:
    """
    Пагинированная клавиатура для отображения списка ключ-значение

    :param items: список кортежей (ключ, значение) для отображения
    :param page: номер текущей страницы (начиная с 0)
    :param back_cb: callback_data для кнопки "Назад"
    :param page_cb_prefix: префикс callback_data для навигации по страницам
    :param page_size: количество элементов на странице
    :return: inline-клавиатура со списком элементов и навигацией
    """
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    kb = InlineKeyboardBuilder()

    # По 2 в ряд для читаемости
    row: list[InlineKeyboardButton] = []
    for key, val in page_items:
        text = f"{key}: {fmt_int(val)}"
        row.append(InlineKeyboardButton(text=text, callback_data="stats:nop"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    # Навигация
    has_prev = page > 0
    has_next = end < len(items)
    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"{page_cb_prefix}:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"{page_cb_prefix}:{page + 1}"))
    if nav:
        kb.row(*nav)

    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb))
    return kb.as_markup()


# ============================================================================
# Клавиатуры управления ролями (/roles)
# ============================================================================

def build_roles_menu_kb() -> types.InlineKeyboardMarkup:
    """
    Главное меню управления ролями пользователей

    :return: inline-клавиатура с категориями пользователей
    """
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="roles:view:users:page:0"),
        InlineKeyboardButton(text="🛡️ Администраторы", callback_data="roles:view:admins:page:0"),
    )
    kb.row(InlineKeyboardButton(text="📋 Все", callback_data="roles:view:all:page:0"))
    return kb.as_markup()
