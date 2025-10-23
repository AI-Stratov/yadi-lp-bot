from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.domain.entities.course import get_course
from bot.domain.entities.mappings import StudyCourses, StudyGroups
from bot.domain.entities.states import SettingsStates
from bot.domain.entities.user import UpdateUserEntity
from bot.domain.services.user import UserServiceInterface
from bot.application.widgets.keyboards import build_courses_kb, build_groups_kb
from dishka import FromDishka
from dishka.integrations.aiogram import inject

router = Router(name="settings")


@router.message(Command("set"))
async def cmd_set(message: types.Message, state: FSMContext):
    """
    Открыть мастер выбора курса и группы пользователя.

    :param message: входящее сообщение пользователя
    :param state: FSM-состояние
    """
    await state.clear()

    await message.answer(
        "Выбери свой курс:",
        reply_markup=build_courses_kb(),
    )
    await state.set_state(SettingsStates.choosing_course)


@router.callback_query(SettingsStates.choosing_course, F.data.startswith("course:"))
async def course_chosen(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка выбора курса.

    :param callback: callback-запрос
    :param state: FSM-состояние
    """
    await callback.answer()
    course_code_value = callback.data.split(":", 1)[1]

    try:
        course_code = StudyCourses(course_code_value)
    except ValueError:
        await callback.message.answer("Некорректный выбор. Попробуйте ещё раз /set")
        await state.clear()
        return

    course = get_course(course_code)
    if not course:
        await callback.message.answer("Не удалось найти курс. Попробуйте /set снова.")
        await state.clear()
        return

    await callback.message.edit_text(
        f"Курс: {course.title}\nТеперь выбери свою группу:",
        reply_markup=build_groups_kb(course),
    )
    await state.set_state(SettingsStates.choosing_group)


@router.callback_query(SettingsStates.choosing_group, F.data.startswith("group:"))
@inject
async def group_chosen(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_service: FromDishka[UserServiceInterface],
):
    """
    Обработка выбора группы; сохраняет курс и группу пользователя.

    :param callback: callback-запрос
    :param state: FSM-состояние
    :param user_service: сервис пользователей
    """
    await callback.answer()

    # Ожидаем формат: group:<COURSE_CODE>:<GROUP_VALUE>
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.message.answer("Некорректный формат выбора. Попробуйте /set")
        await state.clear()
        return

    _, course_code_value, group_value = parts

    try:
        course_enum = StudyCourses(course_code_value)
        group_enum = StudyGroups(group_value)
    except ValueError:
        await callback.message.answer("Некорректный выбор. Попробуйте ещё раз /set")
        await state.clear()
        return

    update = UpdateUserEntity(user_course=course_enum, user_study_group=group_enum)
    await user_service.update_user(callback.from_user.id, update)

    await state.clear()

    course = get_course(course_enum)
    course_title = course.title if course else f"{course_enum}"

    await callback.message.edit_text(
        (
            "✅ Настройки сохранены!\n"
            f"Курс: {course_title}\n"
            f"Группа: {group_enum}\n\n"
            "Теперь я буду присылать уведомления по твоей группе.\n"
            "Используй /settings чтобы задать настройки уведомлений."
        )
    )
