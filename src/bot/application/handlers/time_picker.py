from datetime import time

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


class TimePicker:
    def __init__(self, time_router):
        self.router = time_router
        self._setup_handlers()

    def _setup_handlers(self):
        @self.router.callback_query(lambda c: c.data.startswith("time_"))
        async def process_time_callback(callback: types.CallbackQuery, state: FSMContext, dao: HolderDao):
            state_data = await state.get_data()
            current_time = state_data.get("current_time") or time(10, 0)

            # Обработка изменения времени
            if callback.data in {"time_hour_up", "time_hour_down", "time_minute_up", "time_minute_down"}:
                new_time = self._process_time_change(callback.data, current_time)

                if new_time != current_time:
                    await state.update_data(current_time=new_time)
                    await callback.message.edit_reply_markup(reply_markup=self.create_time_keyboard(new_time))
                await callback.answer()

            # Подтверждение времени
            elif callback.data == "time_confirm":
                await callback.message.edit_text(f'✅ Выбрано время: {current_time.strftime("%H:%M")}')
                await dao.user.update_task_send_time(callback.from_user.id, current_time)
                await state.clear()
                await callback.answer("Время подтверждено!")

            # Отмена выбора времени
            elif callback.data == "time_cancel":
                await callback.message.delete()
                await state.clear()
                await callback.answer("Выбор времени отменен.")

    @staticmethod
    def create_time_keyboard(current_time=None):
        if current_time is None:
            current_time = time(10, 0)

        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="⬅️", callback_data="time_hour_down"),
            InlineKeyboardButton(text=f"{current_time.hour:02d}", callback_data="time_hour"),
            InlineKeyboardButton(text="➡️", callback_data="time_hour_up"),
        )
        keyboard.row(
            InlineKeyboardButton(text="⬅️", callback_data="time_minute_down"),
            InlineKeyboardButton(text=f"{current_time.minute:02d}", callback_data="time_minute"),
            InlineKeyboardButton(text="➡️", callback_data="time_minute_up"),
        )
        keyboard.row(
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="time_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="time_cancel"),
        )

        return keyboard.as_markup()

    def _process_time_change(self, callback_data, current_time):
        if callback_data == "time_hour_up":
            return self._adjust_time(current_time, hours=1)
        elif callback_data == "time_hour_down":
            return self._adjust_time(current_time, hours=-1)
        elif callback_data == "time_minute_up":
            return self._adjust_time(current_time, minutes=15)
        elif callback_data == "time_minute_down":
            return self._adjust_time(current_time, minutes=-15)
        return current_time

    @staticmethod
    def _adjust_time(current_time, hours=0, minutes=0):
        new_hour = (current_time.hour + hours) % 24
        new_minute = (current_time.minute + minutes) % 60

        if current_time.minute + minutes >= 60:
            new_hour += 1
        elif current_time.minute + minutes < 0:
            new_hour -= 1

        return time(new_hour, new_minute)

    @staticmethod
    def _increment_minute(current_datetime, step=15):
        new_minute = (current_datetime.minute + step) % 60
        new_hour = current_datetime.hour + (1 if new_minute < current_datetime.minute else 0)
        return current_datetime.replace(hour=new_hour % 24, minute=new_minute)

    @staticmethod
    def _decrement_minute(current_datetime, step=15):
        new_minute = (current_datetime.minute - step + 60) % 60
        new_hour = current_datetime.hour - (1 if new_minute > current_datetime.minute else 0)
        return current_datetime.replace(hour=new_hour % 24, minute=new_minute)


time_picker = TimePicker(router)
