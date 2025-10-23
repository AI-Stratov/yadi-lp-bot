"""Форматтеры для отображения данных в интерфейсе"""

from bot.domain.entities.statistics import StatsSnapshot
from bot.common.utils.formatting import fmt_int, human_ago


class StatisticsFormatter:
    """Форматирование статистики для отображения в интерфейсе"""

    @staticmethod
    def format_summary(snap: StatsSnapshot) -> str:
        """
        Форматировать общую статистику

        :param snap: снапшот статистики
        :return: отформатированный текст
        """
        lines: list[str] = []
        lines.append("📊 <b>Статистика пользователей</b>")
        lines.append(f"• Всего: <b>{fmt_int(snap.users_total)}</b>")
        lines.append(f"• Уведомления включены: <b>{fmt_int(snap.users_enabled)}</b>")

        if snap.by_course:
            parts = ", ".join(f"{k}: {fmt_int(v)}" for k, v in sorted(snap.by_course.items()))
            lines.append(f"• По курсам: {parts}")
        if snap.by_group:
            parts = ", ".join(f"{k}: {fmt_int(v)}" for k, v in sorted(snap.by_group.items()))
            lines.append(f"• По группам: {parts}")

        lines.append("")
        lines.append("🧩 <b>Уведомления</b>")
        lines.append(f"• В очереди задач: <b>{fmt_int(snap.queue_len)}</b>")
        lines.append(f"• Запланировано к отправке: <b>{fmt_int(snap.scheduled_total)}</b>")

        lines.append("")
        lines.append("📁 <b>Файлы на диске</b>")
        if getattr(snap, "disk_computed_at", None) is None:
            lines.append("• Обновляется… (подождите до 5 минут)")
        else:
            if getattr(snap, "disk_groups", None):
                parts = ", ".join(f"{k}: {fmt_int(v)}" for k, v in sorted(snap.disk_groups.items()))
                lines.append(f"• По группам: {parts}")
            lines.append(f"• Общие (без группы): <b>{fmt_int(getattr(snap, 'disk_common', 0))}</b>")
            lines.append(
                f"• Обновлено: {snap.disk_computed_at.strftime('%d.%m.%Y %H:%M:%S')} ({human_ago(snap.disk_computed_at)})"
            )

        lines.append("")
        lines.append("🚫 <b>Топ отключённых дисциплин</b>")
        if getattr(snap, "top_excluded", None):
            top_disabled = ", ".join(f"{k}×{v}" for k, v in snap.top_excluded.items())
        else:
            top_disabled = "—"
        lines.append(top_disabled)

        return "\n".join(lines)

