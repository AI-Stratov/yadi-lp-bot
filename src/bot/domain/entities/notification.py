from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationTask(BaseModel):
    """Задача на рассылку, формируемая лонг-поллом.
    Содержит минимум данных о найденном файле; маршрутизацию по курсам/группам и фильтры
    выполняет сервис уведомлений.
    """

    subject_code: Optional[str] = None
    subject_title: Optional[str] = None

    file_name: str
    file_path: str
    download_url: Optional[str] = None

    md5: Optional[str] = None
    resource_id: Optional[str] = None
    modified_iso: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now())
