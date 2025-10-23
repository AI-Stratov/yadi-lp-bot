from datetime import datetime, time

from aiogram import types
from pydantic import BaseModel, Field

from bot.domain.entities.mappings import (
    StudyCourses,
    StudyGroups,
    NotificationScheduleMode,
    UserType,
)


class UserBaseEntity(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_bot: bool | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class UserEntity(UserBaseEntity):
    tg_id: int
    user_course: StudyCourses | None = Field(default=None, description="Курс пользователя")
    user_study_group: StudyGroups | None = Field(default=None, description="Группа пользователя")
    excluded_disciplines: set[str] | None = Field(default_factory=set, description="Отключённые дисциплины")

    # Роль пользователя
    user_type: UserType = Field(default=UserType.USER)

    enable_notifications: bool = Field(default=True, description="Настройки уведомлений")

    # Планирование доставки
    notification_mode: NotificationScheduleMode | None = Field(default=None, description="Режим доставки уведомлений")
    task_send_time: time | None = Field(default=None, description="Время отправки уведомлений (если AT_TIME)")
    delivery_window_start: time | None = Field(default=None, description="Начало окна (если IN_WINDOW)")
    delivery_window_end: time | None = Field(default=None, description="Конец окна (если IN_WINDOW)")

    @property
    def display_name(self) -> str:
        """Отображаемое имя пользователя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        return f"User {self.tg_id}"


class CreateUserEntity(BaseModel):
    tg_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_bot: bool | None = None

    @classmethod
    def from_aiogram(cls, user: types.User) -> "CreateUserEntity":
        """Создание сущности из aiogram User"""
        return cls(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_bot=user.is_bot,
        )


class UpdateUserEntity(BaseModel):
    user_course: StudyCourses | None = None
    user_study_group: StudyGroups | None = None
    excluded_disciplines: set[str] | None = None

    # Роль
    user_type: UserType | None = None

    enable_notifications: bool | None = None

    notification_mode: NotificationScheduleMode | None = None
    task_send_time: time | None = None
    delivery_window_start: time | None = None
    delivery_window_end: time | None = None
