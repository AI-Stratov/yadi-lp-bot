from datetime import datetime, time, timedelta
from typing import Optional

from bot.common.logs import logger
from bot.domain.entities.mappings import NotificationScheduleMode, COURSE_SUBJECTS
from bot.domain.entities.notification import NotificationTask, UserNotification
from bot.domain.entities.user import UserEntity
from bot.domain.repositories.notification import NotificationRepositoryInterface
from bot.domain.services.notification import NotificationServiceInterface
from bot.domain.services.user import UserServiceInterface


class NotificationService(NotificationServiceInterface):
    """Сервис обработки уведомлений с фильтрацией и планированием"""

    def __init__(
        self,
        notification_repository: NotificationRepositoryInterface,
        user_service: UserServiceInterface,
    ):
        self.repository = notification_repository
        self.user_service = user_service

    async def enqueue_many(self, tasks: list[NotificationTask]) -> None:
        """Добавляет задачи в общую очередь для обработки"""
        await self.repository.push_to_queue(tasks)
        logger.info(f"📥 Добавлено {len(tasks)} задач в очередь уведомлений")

    async def process_queue(self) -> int:
        """Обрабатывает очередь: распределяет уведомления по пользователям с учетом их настроек"""
        processed = 0

        # Получаем всех пользователей
        users = await self.user_service.list_all_users()

        # Обрабатываем задачи из очереди
        async for task in await self.repository.pop_from_queue():
            # Для каждого пользователя проверяем, нужно ли ему это уведомление
            for user in users:
                if await self._should_notify_user(user, task):
                    # Определяем время отправки
                    scheduled_at = self._calculate_send_time(user, task)

                    # Создаем персональное уведомление
                    notification = UserNotification(
                        user_id=user.tg_id,
                        task=task,
                        created_at=datetime.now(),
                        scheduled_at=scheduled_at,
                    )

                    await self.repository.save_user_notification(notification)
                    processed += 1

        if processed > 0:
            logger.info(f"✅ Обработано {processed} уведомлений")

        return processed

    async def _should_notify_user(self, user: UserEntity, task: NotificationTask) -> bool:
        """Проверяет, должен ли пользователь получить уведомление"""

        # Проверка: уведомления включены
        if not user.enable_notifications:
            return False

        # Проверка: настроен курс
        if not user.user_course:
            return False

        # Проверка: если файл привязан к конкретной группе, то только этой группе
        if not self._matches_user_group(user, task):
            return False

        # Проверка: файл относится к предметам курса пользователя
        if not self._matches_user_course(user, task):
            return False

        # Проверка: предмет не исключен пользователем
        if user.excluded_disciplines and task.subject_code in user.excluded_disciplines:
            return False

        # Проверка: дубликат
        if await self.repository.is_duplicate(user.tg_id, task):
            return False

        return True

    def _matches_user_group(self, user: UserEntity, task: NotificationTask) -> bool:
        """True, если ограничение по группе не нарушено.
        - Если у задачи нет явной группы (лекция общая) - не ограничиваем по группе.
        - Если у задачи есть группа, то уведомляем только пользователей этой группы.
        - Если найден 'похожий на группу' сегмент, но группа неизвестна - считаем нестандартным и не отправляем.
        """
        # Если в пути присутствует сегмент, похожий на группу, но он не распознан
        if getattr(task, "group_raw", None) and not getattr(task, "study_group", None):
            return False

        # Общая для курса запись (например, Лекция без папки группы)
        if not getattr(task, "study_group", None):
            return True

        # Для групповой записи у пользователя должна быть задана совпадающая группа
        return user.user_study_group is not None and user.user_study_group == task.study_group

    def _matches_user_course(self, user: UserEntity, task: NotificationTask) -> bool:
        """Проверяет, относится ли файл к курсу пользователя"""
        # Если не удалось определить предмет - считаем файл нестандартным и не отправляем
        if not task.subject_code:
            return False

        # Получаем предметы для курса пользователя
        course_subjects = COURSE_SUBJECTS.get(user.user_course, [])

        # Если для курса нет определённых предметов - не рискуем и не отправляем
        if not course_subjects:
            return False

        # Проверяем, есть ли предмет в списке для курса
        return task.subject_code in course_subjects

    def _calculate_send_time(self, user: UserEntity, task: NotificationTask) -> Optional[datetime]:
        """Рассчитывает время отправки с учетом настроек пользователя"""
        now = datetime.now()

        # Если режим не настроен, отправляем сразу
        if not user.notification_mode:
            return now

        # Немедленная отправка
        if user.notification_mode == NotificationScheduleMode.ASAP:
            return now

        # Отправка в определенное время
        if user.notification_mode == NotificationScheduleMode.AT_TIME:
            if user.task_send_time:
                return self._next_scheduled_time(user.task_send_time)
            return now

        # Отправка в окне времени
        if user.notification_mode == NotificationScheduleMode.IN_WINDOW:
            if user.delivery_window_start and user.delivery_window_end:
                return self._next_window_time(user.delivery_window_start, user.delivery_window_end)
            return now

        return now

    def _next_scheduled_time(self, target_time: time) -> datetime:
        """Возвращает следующее время отправки для режима AT_TIME"""
        now = datetime.now()
        scheduled = now.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=0,
            microsecond=0
        )

        # Если время уже прошло сегодня, планируем на завтра
        if scheduled <= now:
            scheduled = scheduled + timedelta(days=1)

        return scheduled

    def _next_window_time(self, window_start: time, window_end: time) -> datetime:
        """Возвращает следующее время отправки для режима IN_WINDOW"""
        now = datetime.now()

        # Создаем datetime для начала и конца окна сегодня
        start_today = now.replace(
            hour=window_start.hour,
            minute=window_start.minute,
            second=0,
            microsecond=0
        )
        end_today = now.replace(
            hour=window_end.hour,
            minute=window_end.minute,
            second=0,
            microsecond=0
        )

        # Если сейчас внутри окна, отправляем немедленно
        if start_today <= now <= end_today:
            return now

        # Если окно еще не наступило сегодня, планируем на начало окна
        if now < start_today:
            return start_today

        # Если окно уже прошло сегодня, планируем на начало окна завтра
        return start_today + timedelta(days=1)
