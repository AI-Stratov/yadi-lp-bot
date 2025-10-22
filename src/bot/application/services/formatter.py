from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from bot.domain.entities.material import Material


class NotificationFormatter:
    """Единый форматтер сообщений об учебных материалах."""

    @staticmethod
    def build_text(m: Material) -> str:
        # Пример:
        # 📚 Линейная алгебра
        # 📅 21.10 08:04
        # 👨‍🏫 Медведь Н.Ю.
        # 📖 Лекция
        # 📖 ЛА
        dt = m.created_at.strftime("%d.%m %H:%M")
        teacher = f"\n👨‍🏫 {m.teacher}" if m.teacher else ""
        return (
            f"📚 {m.subject_title}\n"
            f"📅 {dt}{teacher}\n"
            f"📖 {m.topic}\n"
            f"📖 {m.subject_code}"
        )

    @staticmethod
    def build_keyboard(m: Material) -> InlineKeyboardMarkup:
        # Кнопки поиска в текущем чате по теме и предмету
        kb = InlineKeyboardBuilder()
        kb.button(text=f"🔎 {m.topic}", switch_inline_query_current_chat=str(m.topic))
        kb.button(text=f"🔎 {m.subject_code}", switch_inline_query_current_chat=m.subject_title)
        if m.public_url:
            kb.button(text="🔗 Открыть", url=m.public_url)
        kb.adjust(2)
        return kb.as_markup()
