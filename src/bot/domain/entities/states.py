from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    choosing_course = State()
    choosing_group = State()


class NotificationSettingsStates(StatesGroup):
    menu = State()
    choosing_mode = State()
    picking_time = State()
    picking_window_start = State()
    picking_window_end = State()
    picking_subjects = State()
