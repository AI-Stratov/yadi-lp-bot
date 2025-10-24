"""Утилиты форматирования текста, чисел, дат и времени."""
from datetime import datetime, time


def parse_dt_raw(value: str | bytes | None) -> datetime | None:
    """
    Парсинг datetime из сырой строки или bytes

    :param value: сырое значение datetime (строка или bytes в ISO формате)
    :return: распарсенный datetime без timezone, или None при ошибке
    """
    if not value:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def fmt_secs(v: float | int | str) -> str:
    """
    Форматирование значения секунд для отображения

    :param v: количество секунд (float, int или string)
    :return: отформатированная строка вида "5 с" или "3.2 с"
    """
    try:
        num = float(v)
        if abs(num - int(num)) < 1e-9:
            return f"{int(num)} с"
        return f"{num:.1f} с"
    except Exception:
        return str(v)


def fmt_int(n: int) -> str:
    """
    Форматирование целого числа с разделителем тысяч

    :param n: целое число
    :return: отформатированная строка вида "1 234 567"
    """
    try:
        return f"{int(n):,}".replace(",", " ")
    except Exception:
        return str(n)


def human_ago(dt: datetime | None) -> str:
    """
    Форматирование datetime как человекочитаемое относительное время

    :param dt: datetime для форматирования
    :return: строка вида "5 мин назад", "2 ч назад", "3 дн назад"
    """
    if not dt:
        return "—"
    now = datetime.now()
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs} сек назад"
    mins = secs // 60
    if mins < 60:
        return f"{mins} мин назад"
    hours = mins // 60
    if hours < 24:
        return f"{hours} ч назад"
    days = hours // 24
    return f"{days} дн назад"


def fmt_time(t: time | None) -> str:
    """
    Форматирование объекта time как строка HH:MM

    :param t: объект time для форматирования
    :return: отформатированная строка вида "14:30" или пустая строка если None
    """
    return t.strftime("%H:%M") if t else ""


def time_to_str(t: time) -> str:
    """
    Конвертация объекта time в строку формата HH:MM

    :param t: объект time
    :return: строковое представление вида "14:30"
    """
    return t.strftime("%H:%M")


def str_to_time(s: str | None, default: time) -> time:
    """
    Парсинг времени из строки формата HH:MM

    :param s: строка для парсинга (формат: "HH:MM")
    :param default: значение по умолчанию при ошибке парсинга
    :return: распарсенный объект time или значение по умолчанию
    """
    if not s:
        return default
    try:
        hh, mm = s.split(":")
        return time(int(hh), int(mm))
    except Exception:
        return default


def format_notification_message(task) -> str:
    """
    Форматирование задачи уведомления как HTML-сообщение для Telegram

    :param task: объект NotificationTask с метаданными файла
    :return: отформатированная HTML-строка сообщения
    """
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
        """Конвертация строки в валидный формат хэштега."""
        import re
        tag = re.sub(r"[\s.]+", "_", value.strip())
        tag = re.sub(r"[^0-9A-Za-zА-Яа-яЁё_]+", "", tag)
        tag = re.sub(r"_+", "_", tag).strip("_")
        return tag

    hashtags: list[str] = []
    # Тема (лекция/семинар)
    if getattr(task, "topic", None):
        hashtags.append(f"#{sanitize_tag(task.topic.lower())}")
    # Группа
    if getattr(task, "study_group", None):
        hashtags.append(f"#{sanitize_tag(str(task.study_group))}")
    # Предмет (код)
    if getattr(task, "subject_code", None):
        hashtags.append(f"#{sanitize_tag(task.subject_code)}")
    # Преподаватель (как доп. тег для поиска)
    if teacher:
        hashtags.append(f"#{sanitize_tag(teacher)}")

    # Выбираем ссылку: download_url предпочтительнее, иначе public_url
    public_link = task.public_url or ""
    download_link = task.download_url or ""

    # Собираем сообщение
    lines: list[str] = [f"📚 <b>{subject_display or 'Неизвестно'}</b>"]
    if lesson_date_str:
        lines.append(f"📅 {lesson_date_str}")
    if teacher:
        lines.append(f"👨‍🏫 {teacher}")
    if hashtags:
        for h in hashtags:
            # Разносим тегами по смыслу
            if h.startswith('#лекция') or h.startswith('#семинар'):
                lines.append(f"💼 {h}")
            elif getattr(task, "study_group", None) and h.endswith(str(task.study_group)):
                lines.append(f"👥 {h}")
            elif getattr(task, "subject_code", None) and h.endswith(task.subject_code):
                lines.append(f"📖 {h}")
            else:
                lines.append(f"🏷️ {h}")
    if public_link:
        lines.append(f"\n🔗 <a href='{public_link}'>Смотреть видео</a>")
    if download_link:
        lines.append(f"🔗 <a href='{download_link}'>Скачать видео</a>")
    else:
        lines.append(f"\n📄 Файл: {task.file_name}")

    return "\n".join(lines)
