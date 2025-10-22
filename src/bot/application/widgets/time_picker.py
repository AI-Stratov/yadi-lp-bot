from datetime import time
from typing import Literal, Tuple

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


DEFAULT_MINUTE_STEP = 15


def build_time_keyboard(current_time: time, *, prefix: str = "tp", show_cancel: bool = True) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура тайм-пикера.
    callback_data формата: "{prefix}:hour_up|hour_down|min_up|min_down|confirm|cancel".
    """
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:hour_down"),
        InlineKeyboardButton(text=f"{current_time.hour:02d}", callback_data=f"{prefix}:hour"),
        InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:hour_up"),
    )
    kb.row(
        InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:min_down"),
        InlineKeyboardButton(text=f"{current_time.minute:02d}", callback_data=f"{prefix}:min"),
        InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:min_up"),
    )
    actions = [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{prefix}:confirm")]
    if show_cancel:
        actions.append(InlineKeyboardButton(text="❌ Отмена", callback_data=f"{prefix}:cancel"))
    kb.row(*actions)
    return kb.as_markup()


def adjust_time(cur: time, *, dh: int = 0, dm: int = 0) -> time:
    h = (cur.hour + dh) % 24
    total_m = cur.minute + dm
    if total_m >= 60:
        h = (h + (total_m // 60)) % 24
    elif total_m < 0:
        # перескок назад по часам при отрицательных минутах
        h = (h - (abs(total_m) // 60 + (1 if abs(total_m) % 60 else 0))) % 24
    m = total_m % 60
    return time(h, m)


def handle_time_callback(
    callback_data: str,
    current_time: time,
    *,
    prefix: str = "tp",
    minute_step: int = DEFAULT_MINUTE_STEP,
) -> Tuple[time, Literal["update", "confirm", "cancel", "noop"]]:
    """
    Обрабатывает callback_data тайм-пикера и возвращает новое время и действие.
    """
    if not callback_data.startswith(f"{prefix}:"):
        return current_time, "noop"

    action = callback_data.split(":", 1)[1]
    if action == "hour_up":
        return adjust_time(current_time, dh=1), "update"
    if action == "hour_down":
        return adjust_time(current_time, dh=-1), "update"
    if action == "min_up":
        return adjust_time(current_time, dm=minute_step), "update"
    if action == "min_down":
        return adjust_time(current_time, dm=-minute_step), "update"
    if action == "confirm":
        return current_time, "confirm"
    if action == "cancel":
        return current_time, "cancel"

    return current_time, "noop"
