from pydantic import BaseModel
from typing import Optional, Any


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    display_name: str


class RiskResponse(BaseModel):
    risk_score: Optional[float]
    risk_band: Optional[str]
    components: Optional[dict]
    confidence: float
    data_status: str
    explanation: str
    fallback: bool
    snapshot_id: Optional[int]
    snapshot_time: Optional[str]
    asset_count: Optional[int]


class MigrationRequest(BaseModel):
    case_ids: Optional[list[str]] = None


class RollbackRequest(BaseModel):
    case_ids: Optional[list[str]] = None
    reason: str = "manual rollback"
