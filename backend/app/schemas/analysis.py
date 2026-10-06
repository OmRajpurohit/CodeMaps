from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalysisTriggerRequest(BaseModel):
    branch: str | None = Field(None, description="Optional branch or commit SHA override")
    force_fresh: bool = Field(False, description="Force fresh clone ignoring any cache")


class AnalysisRunResponse(BaseModel):
    id: str
    repository_id: str
    commit_sha: str
    status: str
    error_message: str | None = None
    summary_stats: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RepositoryOverviewResponse(BaseModel):
    repository_id: str
    name: str
    url: str
    commit_sha: str
    status: str
    total_files: int
    total_symbols: int
    total_loc: int
    primary_language: str | None
    languages_breakdown: dict[str, int]
    health_score: float
    total_cycles: int
    total_violations: int
    total_hotspots: int
