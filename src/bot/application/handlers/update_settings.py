# from datetime import time
#
# from aiogram import Router
# from aiogram.filters import Command
# from aiogram.fsm.context import FSMContext
# from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
# from aiogram.utils.keyboard import InlineKeyboardBuilder
#
# from dao.holder import HolderDao
# from entities.states import JiraUpdateStates
# from entities.user import UserEntity
# from entities.validator import InputValidation
# from handlers.errors import TelegramLogger
# from handlers.projects_picker import project_picker
# from handlers.status_picker import status_picker
# from handlers.time_picker import time_picker
# from project_logger import logger
# from services.jira import JiraTaskManager
#
# router = Router()
#
#
# @router.message(Command("update"))
# async def update_settings(message: Message):
#     keyboard = InlineKeyboardBuilder()
#     keyboard.row(
#         InlineKeyboardButton(text="🔑 Токен", callback_data="update_token"),
#         InlineKeyboardButton(text="📧 Email", callback_data="update_email"),
#     )
#     keyboard.row(
#         InlineKeyboardButton(text="📅 Дней до дедлайна", callback_data="update_days_until"),
#         InlineKeyboardButton(text="🕒 Время отправки задач", callback_data="update_task_time"),
#     )
#     keyboard.row(
#         InlineKeyboardButton(text="📁 Проекты", callback_data="update_excluded_projects"),
#         InlineKeyboardButton(text="📊 Статусы", callback_data="update_excluded_statuses"),
#     )
#
#     await message.reply("Выберите параметр для обновления:", reply_markup=keyboard.as_markup())
#
#
# @router.callback_query(lambda c: c.data.startswith("update_"))
# async def process_update_callback(callback: CallbackQuery, state: FSMContext, dao: HolderDao):
#     if callback.data == "update_token":
#         await callback.message.answer("🔑 Введите новый токен:")
#         await state.set_state(JiraUpdateStates.waiting_for_token)
#
#     elif callback.data == "update_email":
#         await callback.message.answer("📧 Введите новый email:")
#         await state.set_state(JiraUpdateStates.waiting_for_email)
#
#     elif callback.data == "update_days_until":
#         current_days = await dao.user.get_days_until_deadline(callback.from_user.id)
#         await callback.message.answer(f"📅 За сколько дней до дедлайна уведомлять о задачах? (Текущее значение: {current_days} дн.)")
#         await state.set_state(JiraUpdateStates.waiting_for_days_until)
#
#     elif callback.data == "update_task_time":
#         current_time = await dao.user.get_task_send_time(callback.from_user.id)
#         time_keyboard = time_picker.create_time_keyboard(current_time or time(10, 0))
#         await callback.message.answer("🕒 Выберите время отправки задач:", reply_markup=time_keyboard)
#         await state.set_state(JiraUpdateStates.waiting_for_task_time)
#         await state.update_data(current_time=current_time or time(10, 0))
#
#     elif callback.data == "update_excluded_projects":
#         user: UserEntity = await InputValidation.check_user_settings(callback.message, dao, callback.from_user.id)
#         current_excluded_projects = await dao.user.get_user_excluded_projects(callback.from_user.id)
#
#         all_projects = await JiraTaskManager.get_jira_projects_by_request(user)
#         await state.update_data(
#             excluded_projects=current_excluded_projects,
#             current_page=0,
#             all_projects=all_projects,
#         )
#
#         keyboard = await project_picker.create_project_keyboard(
#             user,
#             page=0,
#             excluded_projects=current_excluded_projects,
#             projects=all_projects,
#         )
#         await callback.message.answer("📁 Выберите проекты:", reply_markup=keyboard)
#         await state.set_state(JiraUpdateStates.waiting_for_excluded_projects)
#
#     elif callback.data == "update_excluded_statuses":
#         user: UserEntity = await InputValidation.check_user_settings(callback.message, dao, callback.from_user.id)
#         current_excluded_statuses = await dao.user.get_user_excluded_statuses(callback.from_user.id)
#
#         all_statuses = await JiraTaskManager.get_jira_statuses_by_request(user)
#         await state.update_data(
#             excluded_statuses=current_excluded_statuses,
#             current_page=0,
#             all_statuses=all_statuses,
#         )
#
#         keyboard = await status_picker.create_status_keyboard(
#             user,
#             page=0,
#             excluded_statuses=current_excluded_statuses,
#             statuses=all_statuses,
#         )
#         await callback.message.answer("📁 Выберите статусы задач:", reply_markup=keyboard)
#         await state.set_state(JiraUpdateStates.waiting_for_excluded_statuses)
#
#     await callback.answer()
#
#
# @router.message(JiraUpdateStates.waiting_for_email)
# async def process_update_jira_email(message: Message, state: FSMContext, dao: HolderDao, telegram_logger: TelegramLogger):
#     is_valid, result = InputValidation.validate_email(message.text)
#     if not is_valid:
#         await message.reply(result)
#         return
#
#     try:
#         await dao.user.update_jira_email(tg_id=message.from_user.id, jira_email=result)
#         await message.reply("✅ Email успешно обновлен!")
#     except Exception as e:
#         await message.reply("🚨 Ошибка при обновлении email.")
#         await telegram_logger.log_message(
#             f"🚨  Ошибка при обновлении email\n"
#             f"👤 Username: {message.from_user.username or 'Не указан'}\n\n"
#             f"👤 Ошибка: {e}\n\n"
#             "#set_error\n"
#             "#ERROR",
#             level="ERROR",
#             module="UserModule",
#             additional_info={
#                 "user_id": message.from_user.id,
#                 "action": "process_update_jira_email",
#             },
#         )
#         logger.error(f"🚨 Ошибка при обновлении email.\n\n {e}")
#     finally:
#         await state.clear()
#
#
# @router.message(JiraUpdateStates.waiting_for_token)
# async def process_update_jira_token(message: Message, state: FSMContext, dao: HolderDao, telegram_logger: TelegramLogger):
#     token = message.text.strip()
#
#     if not token:
#         await message.reply("❌ Токен не может быть пустым.")
#         return
#
#     token_check = InputValidation.validate_jira_token(token)
#     if not token_check["valid"]:
#         error_message = InputValidation.get_error_message(token_check)
#         await message.reply(error_message)
#         return
#
#     try:
#         await dao.user.update_jira_token(tg_id=message.from_user.id, jira_token=token)
#         await message.reply("✅ Токен успешно обновлен!")
#     except Exception as e:
#         await message.reply("🚨 Ошибка при обновлении токена.")
#         await telegram_logger.log_message(
#             f"🚨  Ошибка при обновлении токена\n"
#             f"👤 Username: {message.from_user.username or 'Не указан'}\n\n"
#             f"👤 Ошибка: {e}\n\n"
#             "#set_error\n"
#             "#ERROR",
#             level="ERROR",
#             module="UserModule",
#             additional_info={
#                 "user_id": message.from_user.id,
#                 "action": "process_update_jira_token",
#             },
#         )
#         logger.error(f"🚨 Ошибка при обновлении токена.\n {e}")
#     finally:
#         await state.clear()
#
#
# @router.message(JiraUpdateStates.waiting_for_days_until)
# async def process_days_until(message: Message, state: FSMContext, dao: HolderDao):
#     try:
#         days_until = int(message.text.strip())
#
#         if days_until <= 0:
#             await message.reply("❌ Количество дней должно быть положительным.")
#             return
#
#         if days_until >= 365:
#             await message.reply("❌ Слишком большое число.")
#             return
#
#         await dao.user.update_jira_days_until(tg_id=message.from_user.id, days_until=days_until)
#
#         await message.reply(f"✅ Дней до дедлайна успешно обновлено на {days_until}")
#     except ValueError:
#         await message.reply("❌ Пожалуйста, введите корректное число.")
#     finally:
#         await state.clear()
