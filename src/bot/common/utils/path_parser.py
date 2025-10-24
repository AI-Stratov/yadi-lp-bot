"""Утилиты парсинга путей и имён файлов Яндекс.Диска."""
import re
import urllib.parse
from datetime import datetime
from typing import Any, Optional

from bot.domain.entities.mappings import StudyGroups, SUBJECTS, TOPICS


def parse_datetime(value: Any) -> Optional[datetime]:
    """
    Парсинг datetime из строки или bytes (без timezone)

    :param value: сырое значение datetime (строка или bytes в ISO формате)
    :return: распарсенный naive datetime (без timezone), или None при ошибке
    """
    if not value:
        return None

    if isinstance(value, (bytes, bytearray)):
        value = value.decode()
    try:
        # Убираем timezone из ISO формата
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Возвращаем naive datetime (без timezone)
        return dt.replace(tzinfo=None)
    except Exception:
        return None


def build_public_file_url(file_path: str, public_root_url: str) -> str:
    """
    Построение публичной ссылки Яндекс.Диска на файл

    :param file_path: путь к файлу на диске (например, "/1 курс/МА/file.mp4")
    :param public_root_url: публичная корневая ссылка папки на диске
    :return: прямая ссылка для просмотра файла на Яндекс.Диске
    """
    # Убираем ведущий слэш
    clean_path = file_path.lstrip("/")

    # Разделяем базовую ссылку и параметры
    base_url = public_root_url.split('?')[0].rstrip('/')

    # Формируем полный путь для параметра path
    encoded_path = urllib.parse.quote(clean_path, safe="/")

    # Возвращаем ссылку с параметром path
    return f"{base_url}/{encoded_path}"


def extract_subject_from_path(path: str) -> Optional[str]:
    """
    Извлечение кода предмета из пути к файлу

    Ищет в сегментах пути известные коды предметов из маппинга SUBJECTS.
    Поиск идёт в обратном порядке (от конца к началу) для предпочтения более специфичных совпадений.

    :param path: путь к файлу на диске (например, "/1 курс/МА/БКНАД252/file.mp4")
    :return: код предмета (имя папки) если найдено, иначе None

    :example:
        /// extract_subject_from_path("/1 курс/МА/Лекция/file.mp4")
        "МА"
    """
    try:
        # Разбиваем путь на сегменты и ищем известный предмет
        segments = [s for s in path.replace("\\", "/").split("/") if s]
        for segment in reversed(segments):
            if segment in SUBJECTS:
                return segment
    except Exception:
        pass

    return None


def extract_topic_from_path(path: str) -> Optional[str]:
    """
    Извлечение темы занятия (Лекция/Семинар) из сегментов пути

    :param path: путь к файлу на диске
    :return: название темы если найдено, иначе None

    :example:
        /// extract_topic_from_path("/1 курс/МА/Лекция/file.mp4")
        "Лекция"
    """
    try:
        segments = [s.strip() for s in path.replace("\\", "/").split("/") if s]
        for segment in segments:
            if segment in TOPICS:
                return segment
    except Exception:
        pass
    return None


def extract_group_from_path(path: str) -> Optional[StudyGroups]:
    """
    Извлечение enum учебной группы из пути

    Ищет известные коды групп (например, БКНАД252) в сегментах пути.
    Общие материалы курса (лекции) обычно не имеют папки группы.

    :param path: путь к файлу на диске
    :return: значение enum StudyGroups если найдено, иначе None

    :example:
        /// extract_group_from_path("/1 курс/МА/БКНАД252/file.mp4")
        StudyGroups.BKNAD252
        /// extract_group_from_path("/1 курс/ЛА/Лекция/file.mp4")
        None  # Общая лекция, без конкретной группы
    """
    try:
        segments = [s for s in path.replace("\\", "/").split("/") if s]
        values = {g for g in StudyGroups}
        for segment in segments:
            if segment in values:
                # Вернём enum по значению
                return StudyGroups(segment)
    except Exception:
        pass
    return None


def extract_group_raw_from_path(path: str) -> Optional[str]:
    """
    Поиск сегмента, похожего на код группы (даже если не в enum StudyGroups)

    Ищет сегменты, соответствующие паттерну: ^БКНАД\d{3}$
    Это помогает идентифицировать нестандартные или новые группы, ещё не добавленные в enum.

    :param path: путь к файлу на диске
    :return: сырой код группы (строка) если найден, иначе None

    :example:
    /// extract_group_raw_from_path("/1 курс/МА/БКНАД999/file.mp4")
    "БКНАД999" Даже если не в enum StudyGroups
    """
    segments = [s for s in path.replace("\\", "/").split("/") if s]
    pattern = re.compile(r"^БКНАД\d{3}$", re.IGNORECASE)
    for segment in segments:
        if pattern.match(segment):
            return segment
    return None


def extract_teacher_from_filename(filename: str) -> Optional[str]:
    """
    Извлечение имени преподавателя из имени файла

    Ожидаемый формат: 'Фамилия И.О. 2025-10-15T08-08-19Z.mp4'

    :param filename: имя файла
    :return: имя преподавателя (например, "Лобода А.А.") если найдено, иначе None

    :example:
        /// extract_teacher_from_filename("Лобода А.А. 2025-10-15T08-08-19Z.mp4")
        "Лобода А.А."
    """
    # Паттерн: Фамилия И.О. (кириллица + точки)
    # Примеры: "Лобода А.А.", "Медведь Н.Ю.", "Овчинников С.А."
    pattern = r'^([А-ЯЁа-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.)'
    match = re.match(pattern, filename)

    if match:
        return match.group(1).strip()

    return None


# -------------------- Расширенный парсинг даты/времени --------------------

def _try_build_datetime(year: int, month: int, day: int, hour: int | None, minute: int | None, second: int | None) -> Optional[datetime]:
    try:
        return datetime(year, month, day, hour or 0, minute or 0, second or 0)
    except ValueError:
        return None


def _extract_datetime_from_text(text: str) -> Optional[datetime]:
    """
    Универсальный поиск даты/времени в тексте по нескольким распространённым форматам.

    Поддерживаемые форматы (время необязательно):
    - YYYY-MM-DD[ T|_ ]HH[:|.|-]MM([:|.|-]SS)?(Z)?
    - YYYY-MM-DD
    - DD.MM.YYYY[ T|_ ]HH[:|.|-]MM([:|.|-]SS)?
    - DD.MM.YYYY
    - YYYY.MM.DD[ T|_ ]HH[:|.|-]MM([:|.|-]SS)?
    - YYYY.MM.DD
    """
    if not text:
        return None

    # 1) ISO-подобный: 2025-10-15T08-08-19Z, 2025-10-15 08:08, 2025-10-15_08.08.19
    iso_like = re.search(r'(\d{4})-(\d{2})-(\d{2})(?:[T _](\d{2})[:\-.](\d{2})(?:[:\-.](\d{2}))?Z?)?', text)
    if iso_like:
        y, m, d = int(iso_like.group(1)), int(iso_like.group(2)), int(iso_like.group(3))
        hh = int(iso_like.group(4)) if iso_like.group(4) else None
        mm = int(iso_like.group(5)) if iso_like.group(5) else None
        ss = int(iso_like.group(6)) if iso_like.group(6) else None
        dt = _try_build_datetime(y, m, d, hh, mm, ss)
        if dt:
            return dt

    # 2) ДД.ММ.ГГГГ [время]
    dmy = re.search(r'(\d{2})[.-](\d{2})[.-](\d{4})(?:[T _](\d{2})[.:\-](\d{2})(?:[.:\-](\d{2}))?)?', text)
    if dmy:
        d, m, y = int(dmy.group(1)), int(dmy.group(2)), int(dmy.group(3))
        hh = int(dmy.group(4)) if dmy.group(4) else None
        mm = int(dmy.group(5)) if dmy.group(5) else None
        ss = int(dmy.group(6)) if dmy.group(6) else None
        dt = _try_build_datetime(y, m, d, hh, mm, ss)
        if dt:
            return dt

    # 3) ГГГГ.ММ.ДД [время]
    ymd_dots = re.search(r'(\d{4})[.-](\d{2})[.-](\d{2})(?:[T _](\d{2})[.:\-](\d{2})(?:[.:\-](\d{2}))?)?', text)
    if ymd_dots:
        y, m, d = int(ymd_dots.group(1)), int(ymd_dots.group(2)), int(ymd_dots.group(3))
        hh = int(ymd_dots.group(4)) if ymd_dots.group(4) else None
        mm = int(ymd_dots.group(5)) if ymd_dots.group(5) else None
        ss = int(ymd_dots.group(6)) if ymd_dots.group(6) else None
        dt = _try_build_datetime(y, m, d, hh, mm, ss)
        if dt:
            return dt

    return None


def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Извлечение даты занятия из имени файла

    Поддерживаемые форматы (время опционально):
    - '2025-10-15T08-08-19Z', '2025-10-15 08:08:19', '2025-10-15'
    - '15.10.2025', '15.10.2025 08:08'
    - '2025.10.15'

    :param filename: имя файла
    :return: распарсенный datetime если найден, иначе None

    :example:
        /// extract_date_from_filename("Лобода А.А. 2025-10-15T08-08-19Z.mp4")
        datetime(2025, 10, 15, 8, 8, 19)
    """
    return _extract_datetime_from_text(filename)


def extract_date_from_path(path: str) -> Optional[datetime]:
    """
    Извлечь дату/время занятия из сегментов пути.

    Часто дата указывается в названии папки (например, "Лекция 15.10.2025" или "2025-10-15").
    Сканируем сегменты пути с конца к началу (ближайшие к файлу приоритетнее).
    """
    if not path:
        return None
    segments = [s for s in path.replace('\\', '/').split('/') if s]
    for segment in reversed(segments):
        dt = _extract_datetime_from_text(segment)
        if dt:
            return dt
    return None
