from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ViolationResponse(BaseModel):
    id: str
    source_file_path: str
    target_file_path: str
    rule_name: str
    severity: str
    message: str
    layer_from: str | None = None
    layer_to: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ViolationsListResponse(BaseModel):
    total_violations: int
    violations: list[ViolationResponse]
