"""
Виджет тайм-пикера для выбора времени в Telegram.
"""
from datetime import time
from typing import Literal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.domain.entities.constants import DEFAULT_MINUTE_STEP, DEFAULT_PREFIX


# ============================================================================
# Класс TimePicker - объектно-ориентированный подход
# ============================================================================

class TimePicker:
    """
    Виджет для выбора времени через inline-клавиатуру Telegram

    Позволяет пользователю выбрать время (часы и минуты) с помощью кнопок
    увеличения/уменьшения значений.
    """

    def __init__(
        self,
        *,
        prefix: str = DEFAULT_PREFIX,
        minute_step: int = DEFAULT_MINUTE_STEP,
        show_cancel: bool = True,
    ):
        """
        Инициализация виджета тайм-пикера

        :param prefix: префикс для callback_data (для избежания конфликтов)
        :param minute_step: шаг изменения минут (по умолчанию DEFAULT_MINUTE_STEP)
        :param show_cancel: показывать ли кнопку "Отмена"
        """
        self.prefix = prefix
        self.minute_step = minute_step
        self.show_cancel = show_cancel

    def build_keyboard(self, current_time: time) -> InlineKeyboardMarkup:
        """
        Построение клавиатуры тайм-пикера

        :param current_time: текущее выбранное время
        :return: inline-клавиатура с кнопками управления временем

        Структура клавиатуры:
        [⬅️] [HH] [➡️]
        [⬅️] [MM] [➡️]
        [✅ Подтвердить] [❌ Отмена]
        """
        kb = InlineKeyboardBuilder()

        # Часы
        kb.row(
            InlineKeyboardButton(text="⬅️", callback_data=f"{self.prefix}:hour_down"),
            InlineKeyboardButton(text=f"{current_time.hour:02d}", callback_data=f"{self.prefix}:hour"),
            InlineKeyboardButton(text="➡️", callback_data=f"{self.prefix}:hour_up"),
        )

        # Минуты
        kb.row(
            InlineKeyboardButton(text="⬅️", callback_data=f"{self.prefix}:min_down"),
            InlineKeyboardButton(text=f"{current_time.minute:02d}", callback_data=f"{self.prefix}:min"),
            InlineKeyboardButton(text="➡️", callback_data=f"{self.prefix}:min_up"),
        )

        # Действия
        actions = [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{self.prefix}:confirm")]
        if self.show_cancel:
            actions.append(InlineKeyboardButton(text="❌ Отмена", callback_data=f"{self.prefix}:cancel"))
        kb.row(*actions)

        return kb.as_markup()

    def handle_callback(
        self,
        callback_data: str,
        current_time: time,
    ) -> tuple[time, Literal["update", "confirm", "cancel", "noop"]]:
        """
        Обработка callback от кнопок тайм-пикера

        :param callback_data: данные callback от Telegram
        :param current_time: текущее выбранное время
        :return: кортеж (новое_время, действие)

        Возможные действия:
        - "update": обновить клавиатуру (время изменилось)
        - "confirm": пользователь подтвердил выбор
        - "cancel": пользователь отменил выбор
        - "noop": callback не относится к этому виджету
        """
        if not callback_data.startswith(f"{self.prefix}:"):
            return current_time, "noop"

        action = callback_data.split(":", 1)[1]

        if action == "hour_up":
            return self._adjust_time(current_time, dh=1), "update"
        if action == "hour_down":
            return self._adjust_time(current_time, dh=-1), "update"
        if action == "min_up":
            return self._adjust_time(current_time, dm=self.minute_step), "update"
        if action == "min_down":
            return self._adjust_time(current_time, dm=-self.minute_step), "update"
        if action == "confirm":
            return current_time, "confirm"
        if action == "cancel":
            return current_time, "cancel"

        return current_time, "noop"

    @staticmethod
    def _adjust_time(cur: time, *, dh: int = 0, dm: int = 0) -> time:
        """
        Корректировка времени с учётом переполнения

        :param cur: текущее время
        :param dh: изменение часов (может быть отрицательным)
        :param dm: изменение минут (может быть отрицательным)
        :return: новое скорректированное время

        Обрабатывает переполнение минут в часы и циклическое изменение часов (0-23).
        """
        h = (cur.hour + dh) % 24
        total_m = cur.minute + dm

        if total_m >= 60:
            h = (h + (total_m // 60)) % 24
        elif total_m < 0:
            # перескок назад по часам при отрицательных минутах
            h = (h - (abs(total_m) // 60 + (1 if abs(total_m) % 60 else 0))) % 24

        m = total_m % 60
        return time(h, m)
