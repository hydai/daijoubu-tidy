from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ItemCreate(BaseModel):
    content: str
    content_type: str = "text"
    url: str | None = None
    source_channel: str | None = None


class ItemUpdate(BaseModel):
    content: str | None = None
    content_type: str | None = None


class ItemResponse(BaseModel):
    id: UUID
    content: str
    content_type: str
    url: str | None = None
    url_title: str | None = None
    url_description: str | None = None
    source_channel: str | None = None
    categories: list[str] = []
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
