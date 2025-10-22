from datetime import datetime

from pydantic import BaseModel, Field


class YaDiskFileInfo(BaseModel):
    path: str
    name: str
    type: str | None = None
    size: int | None = None
    modified: datetime
    created: datetime | None = None
    md5: str | None = None
    mime_type: str | None = None
    resource_id: str | None = None
    download_url: str | None = None


class FolderState(BaseModel):
    path: str
    files: dict[str, YaDiskFileInfo] = Field(default_factory=dict)
    last_check: datetime = Field(default_factory=datetime.now)

    def get_key(self) -> str:
        return f"folder_state:{self.path}"
