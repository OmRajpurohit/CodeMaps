from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RepositoryBase(BaseModel):
    url: str = Field(..., description="Git repository clone URL (HTTP/HTTPS/SSH)")
    name: str | None = Field(None, description="Repository name (defaults to path name if omitted)")
    default_branch: str = Field("main", description="Target branch for analysis")


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryResponse(RepositoryBase):
    id: str
    description: str | None = None
    primary_language: str | None = None
    stars: int = 0
    forks: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
