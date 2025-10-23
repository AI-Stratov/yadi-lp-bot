from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StatsSnapshot(BaseModel):
    users_total: int = 0
    users_enabled: int = 0

    by_course: dict[str, int] = Field(default_factory=dict)
    by_group: dict[str, int] = Field(default_factory=dict)
    top_excluded: dict[str, int] = Field(default_factory=dict)

    queue_len: int = 0
    scheduled_total: int = 0

    disk_groups: dict[str, int] = Field(default_factory=dict)
    disk_common: int = 0
    disk_computed_at: Optional[datetime] = None

