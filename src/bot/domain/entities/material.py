from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from bot.domain.entities.mappings import StudyCourses, StudyGroups


class TopicType(StrEnum):
    LECTURE = "Лекция"
    SEMINAR = "Семинар"


class Material(BaseModel):
    subject_code: str
    subject_title: str
    topic: TopicType
    teacher: Optional[str] = None

    course: StudyCourses
    group: StudyGroups

    file_name: str
    file_path: str
    public_url: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now())

    class Config:
        from_attributes = True
