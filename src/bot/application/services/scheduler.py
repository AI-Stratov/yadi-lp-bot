import asyncio
from datetime import datetime

from aiogram import Bot
from aiogram.types import LinkPreviewOptions

from bot.common.logs import logger
from bot.domain.entities.notification import UserNotification
from bot.domain.repositories.notification import NotificationRepositoryInterface


class NotificationScheduler:
    """Планировщик отправки уведомлений по расписанию"""

    def __init__(
        self,
        bot: Bot,
        repository: NotificationRepositoryInterface,
        check_interval: int = 60,  # Проверка каждую минуту
    ):
        self.bot = bot
        self.repository = repository
        self.check_interval = check_interval
        self._running = False
        self._task = None

    async def start(self):
        """Запускает планировщик"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop(), name="notification_scheduler")

    async def stop(self):
        """Останавливает планировщик"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Планировщик уведомлений остановлен")

    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self._running:
            try:
                await self._send_due_notifications()
            except Exception as e:
                logger.exception(f"Ошибка в планировщике уведомлений: {e}")

            await asyncio.sleep(self.check_interval)

    async def _send_due_notifications(self):
        """Отправляет все просроченные уведомления"""
        now = datetime.now()
        sent_count = 0
        failed_count = 0

        logger.debug(f"🔍 Проверка уведомлений до {now.isoformat()}")

        async for notification in self.repository.get_due_notifications(now):
            try:
                await self._send_notification(notification)
                if notification.notification_id:
                    await self.repository.mark_as_sent(notification.notification_id)
                sent_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {notification.user_id}: {e}")
                if notification.notification_id:
                    await self.repository.mark_as_failed(notification.notification_id, str(e))
                failed_count += 1

        if sent_count > 0 or failed_count > 0:
            logger.info(f"📤 Отправлено уведомлений: {sent_count}, ошибок: {failed_count}")
        else:
            logger.debug(f"⏭️ Нет уведомлений для отправки")

    async def _send_notification(self, notification: UserNotification):
        """Отправляет одно уведомление пользователю"""
        task = notification.task
        message = self._format_message(task)

        await self.bot.send_message(
            chat_id=notification.user_id,
            text=message,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

    def _format_message(self, task) -> str:
        """Форматирует сообщение для отправки"""
        from bot.domain.entities.mappings import SUBJECTS

        # Отображаемое имя предмета
        subject_display = SUBJECTS.get(task.subject_code, task.subject_code) if task.subject_code else "Неизвестно"

        # Дата/время занятия
        lesson_date_str = ""
        if task.lesson_date:
            lesson_date_str = task.lesson_date.strftime('%d.%m %H:%M')

        # Преподаватель
        teacher = task.teacher or ""

        # Хэштеги
        def sanitize_tag(value: str) -> str:
            # Превращаем строку в #хэштег: пробелы/точки в подчёркивания, убираем лишнее
            import re
            tag = re.sub(r"[\s\.]+", "_", value.strip())
            tag = re.sub(r"[^0-9A-Za-zА-Яа-яЁё_]+", "", tag)
            tag = re.sub(r"_+", "_", tag).strip("_")
            return tag

        hashtags: list[str] = []
        # Тема (лекция/семинар)
        if getattr(task, "topic", None):
            hashtags.append(f"#{sanitize_tag(task.topic.lower())}")
        # Группа
        if getattr(task, "study_group", None):
            hashtags.append(f"#{sanitize_tag(task.study_group.value)}")
        # Предмет (код - короче и удобнее)
        if getattr(task, "subject_code", None):
            hashtags.append(f"#{sanitize_tag(task.subject_code)}")
        # Преподаватель (как доп. тег для поиска)
        if teacher:
            hashtags.append(f"#{sanitize_tag(teacher)}")

        # Выбираем ссылку: download_url предпочтительнее, иначе public_url
        link = task.download_url or task.public_url or ""

        # Собираем сообщение
        lines: list[str] = []
        lines.append(f"📚 <b>{subject_display or 'Неизвестно'}</b>")
        if lesson_date_str:
            lines.append(f"📅 {lesson_date_str}")
        if teacher:
            lines.append(f"👨‍🏫 {teacher}")
        if hashtags:
            for h in hashtags:
                # Разносим тегами по смыслу, но компактно - один тег в строке с соответствующим эмодзи
                if h.startswith('#лекция') or h.startswith('#семинар'):
                    lines.append(f"💼 {h}")
                elif getattr(task, "study_group", None) and h.endswith(task.study_group.value):
                    lines.append(f"👥 {h}")
                elif getattr(task, "subject_code", None) and h.endswith(task.subject_code):
                    lines.append(f"📖 {h}")
                else:
                    lines.append(f"🏷️ {h}")
        if link:
            lines.append(f"\n🔗 <a href='{link}'>Смотреть видео</a>")
        else:
            lines.append(f"\n📄 Файл: {task.file_name}")

        return "\n".join(lines)
