from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HotspotResponse(BaseModel):
    id: str
    file_id: str | None = None
    file_path: str
    score: float
    churn_score: float
    centrality_score: float
    complexity_score: float
    rationale: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HotspotsListResponse(BaseModel):
    total_hotspots: int
    hotspots: list[HotspotResponse]
