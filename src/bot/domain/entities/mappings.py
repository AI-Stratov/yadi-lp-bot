from enum import StrEnum

from typing import Iterable


class StudyGroups(StrEnum):
    BKNAD251 = "БКНАД251"
    BKNAD252 = "БКНАД252"
    BKNAD253 = "БКНАД253"
    BKNAD241 = "БКНАД241"
    BKNAD242 = "БКНАД242"
    BKNAD231 = "БКНАД231"
    BKNAD232 = "БКНАД232"
    BKNAD211 = "БКНАД211"
    BKNAD212 = "БКНАД212"


class StudyCourses(StrEnum):
    COURSE1 = "COURSE1"
    COURSE2 = "COURSE2"
    COURSE3 = "COURSE3"
    COURSE4 = "COURSE4"


class UserType(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPERUSER = "SUPERUSER"


class NotificationScheduleMode(StrEnum):
    ASAP = "ASAP"  # Сразу по появлению
    AT_TIME = "AT_TIME"  # В определённое время
    IN_WINDOW = "IN_WINDOW"  # В указанном окне времени


class NotificationStatus(StrEnum):
    PENDING = "pending"  # Ожидает отправки
    SENT = "sent"  # Отправлено
    FAILED = "failed"  # Ошибка отправки


# COURSES = {
#     "1": "1 курс",
#     "2": "2 курс",
#     "3": "3 курс",
#     "4": "4 курс",
# }

SUBJECTS = {
    "БЖД": "БЖД",
    "ДМ": "Дискретная математика",
    "История России": "История России",
    "ЛА": "Линейная алгебра",
    "МА": "Математический анализ",
    "Программирование на Python": "Программирование на Python",
    "АиСД2": "Алгоритмы и структуры данных 2",
    "Алгебра": "Алгебра",
    "МА2": "Математический анализ 2",
    "Теория вероятностей": "Теория вероятностей",
    "Глубинное обучение 1": "Глубинное обучение 1",
    "Мат статистика 2": "Математическая статистика 2",
    "Математическая статистика 2": "Математическая статистика 2",
    "Машинное обучение 1": "Машинное обучение 1",
    'НИС "Машинное обучение и приложение 1"': "НИС 'Машинное обучение и приложение 1'",
    'НИС "Промышленное программирование 1"': "НИС 'Промышленное программирование 1'",
    'НИС "Машинное обучение и приложение 2"': "НИС 'Машинное обучение и приложение 2'",
    'НИС "Промышленное программирование 2"': "НИС 'Промышленное программирование 2'",
    "Глубинное обучение 2": "Глубинное обучение 2",
    "ДОЦ Психология": "ДОЦ Психология",
}

TOPICS = {
    "Лекция": "Лекция",
    "Семинар": "Семинар",
}

COURSE_SUBJECTS: dict[StudyCourses, list[str]] = {
    StudyCourses.COURSE1: [
        "БЖД", "ДМ", "История России", "ЛА", "МА", "Программирование на Python"
    ],
    StudyCourses.COURSE2: [
        "АиСД2", "Алгебра", "МА2", "Теория вероятностей"
    ],
    StudyCourses.COURSE3: [
        "Глубинное обучение 1", "Мат статистика 2", "Математическая статистика 2", "Машинное обучение 1",
        'НИС "Машинное обучение и приложение 1"', 'НИС "Промышленное программирование 1"'
    ],
    StudyCourses.COURSE4: [
        "Глубинное обучение 2", "ДОЦ Психология",
        'НИС "Машинное обучение и приложение 2"', 'НИС "Промышленное программирование 2"'
    ],
}


def get_subject_keys_for_course(course: StudyCourses) -> list[str]:
    """Вернуть список ключей предметов (по умолчанию - из COURSE_SUBJECTS; если пусто, fallback на все SUBJECTS)."""
    keys = COURSE_SUBJECTS.get(course) or []
    if keys:
        return keys
    # Fallback: без настроек курса показываем все известные предметы
    return list(SUBJECTS.keys())


def iter_subjects_for_course(course: StudyCourses) -> Iterable[tuple[str, str]]:
    """Итератор по (key, display): key - ключ папки на диске, display - имя из SUBJECTS."""
    for key in get_subject_keys_for_course(course):
        display = SUBJECTS.get(key, key)
        yield key, display
