from datetime import datetime
from typing import Optional

from bot.domain.entities.mappings import NotificationStatus, StudyGroups
from pydantic import BaseModel, Field


class NotificationTask(BaseModel):
    """Задача на рассылку, формируемая лонг-поллом.
    Содержит минимум данных о найденном файле; маршрутизацию по курсам/группам и фильтры
    выполняет сервис уведомлений.
    """

    subject_code: Optional[str] = None
    subject_title: Optional[str] = None
    # Тема занятия (Лекция/Семинар), если удалось определить по пути
    topic: Optional[str] = None

    # Признак/код группы, если файл лежит в папке конкретной группы (например, "БКНАД252").
    study_group: Optional[StudyGroups] = None
    # Сырой сегмент из пути, похожий на группу (для обнаружения неизвестных групп)
    group_raw: Optional[str] = None

    # Метаданные из файла
    teacher: Optional[str] = None  # Имя преподавателя из названия файла
    lesson_date: Optional[datetime] = None  # Дата занятия из названия или метаданных

    file_name: str
    file_path: str
    public_url: Optional[str] = None  # Прямая ссылка на просмотр на Яндекс.Диске
    download_url: Optional[str] = None  # Временная ссылка для скачивания

    md5: Optional[str] = None
    resource_id: Optional[str] = None
    modified_iso: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now())


class UserNotification(BaseModel):
    """Персональное уведомление для пользователя с учетом его настроек доставки"""

    user_id: int
    task: NotificationTask
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    scheduled_at: Optional[datetime] = None  # Когда отправить (None = немедленно)
    status: NotificationStatus = Field(default=NotificationStatus.PENDING)
    notification_id: Optional[str] = None  # Уникальный ID для идемпотентности
