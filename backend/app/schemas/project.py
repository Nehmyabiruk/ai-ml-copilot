from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    repository_url: str | None = Field(
        default=None,
        max_length=500,
    )


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    repository_url: str | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )