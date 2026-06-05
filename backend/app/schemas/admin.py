from pydantic import BaseModel
from datetime import datetime


class AdminUserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    is_verified: bool | None = None


class AdminSessionReview(BaseModel):
    review_status: str  # approved | rejected | needs_revision
    reviewer_notes: str | None = None


class DashboardStats(BaseModel):
    total_users: int
    total_sessions: int
    sessions_today: int
    avg_confidence: float
    pending_reviews: int
    top_icd10_codes: list[dict]
    top_cpt_codes: list[dict]
    accuracy_rate: float


class AuditLogEntry(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str | None
    ip_address: str | None
    outcome: str
    created_at: datetime

    model_config = {"from_attributes": True}
