import asyncio
from datetime import datetime

from aiogram.types import LinkPreviewOptions

from bot.common.logs import logger
from bot.common.utils.formatting import format_notification_message
from bot.domain.entities.notification import UserNotification
from bot.domain.services.scheduler import SchedulerServiceInterface


class NotificationScheduler(SchedulerServiceInterface):
    """
    Планировщик отправки уведомлений по расписанию
    """

    @property
    def check_interval(self) -> int:
        """Периодичность проверки очереди (в секундах)."""
        return self._check_interval

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

        async for notification in self.repository.get_due_notifications(now): # NOQA
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
            logger.debug("⏭️ Нет уведомлений для отправки")

    async def _send_notification(self, notification: UserNotification):
        """Отправляет одно уведомление пользователю"""
        task = notification.task
        message = format_notification_message(task)

        await self.bot.send_message(
            chat_id=notification.user_id,
            text=message,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
